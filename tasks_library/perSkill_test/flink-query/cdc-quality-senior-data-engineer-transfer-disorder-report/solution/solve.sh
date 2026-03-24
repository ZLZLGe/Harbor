#!/bin/bash

set -euo pipefail

mkdir -p /app/workspace/src/main/java/cdcquality/query
mkdir -p /app/workspace/src/main/java/cdcquality/utils
mkdir -p /app/workspace/src/main/java/cdcquality/datatypes

cat <<'EOF' > /app/workspace/src/main/java/cdcquality/datatypes/CdcEvent.java
package cdcquality.datatypes;

import java.io.Serializable;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;

public class CdcEvent implements Serializable {
    public String eventTimeUtc;
    public String tableName;
    public String primaryKey;
    public long changeSeq;
    public String operation;
    public String payload;

    public static CdcEvent fromCsv(String line) {
        String[] parts = line.split(",", 6);
        if (parts.length != 6) {
            throw new IllegalArgumentException("Invalid CDC line: " + line);
        }

        CdcEvent event = new CdcEvent();
        event.eventTimeUtc = parts[0];
        event.tableName = parts[1];
        event.primaryKey = parts[2];
        event.changeSeq = Long.parseLong(parts[3]);
        event.operation = parts[4];
        event.payload = parts[5];
        return event;
    }

    public String entityKey() {
        return tableName + "|" + primaryKey;
    }

    public String reportDate() {
        return LocalDate.ofInstant(Instant.parse(eventTimeUtc), ZoneOffset.UTC).toString();
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/cdcquality/datatypes/MetricDelta.java
package cdcquality.datatypes;

import java.io.Serializable;

public class MetricDelta implements Serializable {
    public String reportDate;
    public String tableName;
    public int duplicateSuppressed;
    public int outOfOrderUpdates;
    public int finalRetainedDelta;

    public MetricDelta() {
    }

    public MetricDelta(
            String reportDate,
            String tableName,
            int duplicateSuppressed,
            int outOfOrderUpdates,
            int finalRetainedDelta) {
        this.reportDate = reportDate;
        this.tableName = tableName;
        this.duplicateSuppressed = duplicateSuppressed;
        this.outOfOrderUpdates = outOfOrderUpdates;
        this.finalRetainedDelta = finalRetainedDelta;
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/cdcquality/query/CdcDisorderQualityReport.java
package cdcquality.query;

import cdcquality.datatypes.CdcEvent;
import cdcquality.datatypes.MetricDelta;
import cdcquality.utils.AppBase;
import org.apache.flink.api.common.functions.FilterFunction;
import org.apache.flink.api.common.functions.FlatMapFunction;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.api.java.utils.ParameterTool;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class CdcDisorderQualityReport extends AppBase {

    public static void main(String[] args) throws Exception {
        ParameterTool params = ParameterTool.fromArgs(args);
        String cdcInput = params.getRequired("cdc_input");
        String outputPath = params.getRequired("output");

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(1);

        DataStream<CdcEvent> events = env
                .readTextFile(cdcInput)
                .filter((FilterFunction<String>) line -> !line.trim().isEmpty())
                .filter((FilterFunction<String>) line -> !line.startsWith("event_time_utc"))
                .flatMap(new ParseEvent());

        DataStream<MetricDelta> deltas = events
                .keyBy(CdcEvent::entityKey)
                .process(new DeduplicateLatestPerKey());

        List<MetricDelta> collected = new ArrayList<>();
        try (var iterator = deltas.executeAndCollect()) {
            while (iterator.hasNext()) {
                collected.add(iterator.next());
            }
        }

        Map<Tuple2<String, String>, ReportTotals> totals = new LinkedHashMap<>();
        for (MetricDelta delta : collected) {
            Tuple2<String, String> key = Tuple2.of(delta.reportDate, delta.tableName);
            ReportTotals current = totals.computeIfAbsent(key, ignored -> new ReportTotals());
            current.duplicateSuppressed += delta.duplicateSuppressed;
            current.outOfOrderUpdates += delta.outOfOrderUpdates;
            current.finalRetainedRecords += delta.finalRetainedDelta;
        }

        List<Map.Entry<Tuple2<String, String>, ReportTotals>> rows = new ArrayList<>(totals.entrySet());
        rows.sort(
                Comparator.comparing((Map.Entry<Tuple2<String, String>, ReportTotals> entry) -> entry.getKey().f0)
                        .thenComparing(entry -> entry.getKey().f1));

        List<String> outputLines = new ArrayList<>();
        for (Map.Entry<Tuple2<String, String>, ReportTotals> row : rows) {
            ReportTotals value = row.getValue();
            if (value.duplicateSuppressed == 0
                    && value.outOfOrderUpdates == 0
                    && value.finalRetainedRecords == 0) {
                continue;
            }
            outputLines.add(
                    "date=" + row.getKey().f0
                            + " table=" + row.getKey().f1
                            + " duplicate_suppressed=" + value.duplicateSuppressed
                            + " out_of_order_updates=" + value.outOfOrderUpdates
                            + " final_retained_records=" + value.finalRetainedRecords);
        }

        Files.write(Path.of(outputPath), outputLines, StandardCharsets.UTF_8);
    }

    public static class ParseEvent implements FlatMapFunction<String, CdcEvent> {
        @Override
        public void flatMap(String value, Collector<CdcEvent> out) {
            out.collect(CdcEvent.fromCsv(value));
        }
    }

    public static class DeduplicateLatestPerKey extends KeyedProcessFunction<String, CdcEvent, MetricDelta> {
        private transient ValueState<CdcEvent> latestState;

        @Override
        public void open(Configuration parameters) {
            latestState = getRuntimeContext().getState(new ValueStateDescriptor<>("latest", CdcEvent.class));
        }

        @Override
        public void processElement(CdcEvent event, Context context, Collector<MetricDelta> out) throws Exception {
            CdcEvent latest = latestState.value();
            if (latest == null) {
                latestState.update(event);
                out.collect(new MetricDelta(event.reportDate(), event.tableName, 0, 0, 1));
                return;
            }

            if (event.changeSeq == latest.changeSeq) {
                out.collect(new MetricDelta(event.reportDate(), event.tableName, 1, 0, 0));
                return;
            }

            if (event.changeSeq < latest.changeSeq) {
                out.collect(new MetricDelta(event.reportDate(), event.tableName, 0, 1, 0));
                return;
            }

            out.collect(new MetricDelta(latest.reportDate(), latest.tableName, 0, 0, -1));
            latestState.update(event);
            out.collect(new MetricDelta(event.reportDate(), event.tableName, 0, 0, 1));
        }
    }

    public static class ReportTotals {
        public int duplicateSuppressed;
        public int outOfOrderUpdates;
        public int finalRetainedRecords;
    }
}
EOF
