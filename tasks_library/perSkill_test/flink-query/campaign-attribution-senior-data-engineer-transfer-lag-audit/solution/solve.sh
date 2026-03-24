#!/bin/bash

set -euo pipefail

mkdir -p /app/workspace/src/main/java/campaignaudit/query
mkdir -p /app/workspace/src/main/java/campaignaudit/utils
mkdir -p /app/workspace/src/main/java/campaignaudit/datatypes
mkdir -p /app/workspace/src/main/java/campaignaudit/sources
mkdir -p /app/workspace/src/main/java/campaignaudit/sinks

cat <<'EOF' > /app/workspace/src/main/java/campaignaudit/datatypes/ImpressionEvent.java
package campaignaudit.datatypes;

import java.io.Serializable;

public class ImpressionEvent implements Serializable {
    public long timestampMicros;
    public String campaignId;
    public String impressionId;
    public String userId;
    public String creativeId;

    public ImpressionEvent() {
    }

    public static ImpressionEvent fromString(String line) {
        String[] tokens = line.split(",", -1);
        if (tokens.length != 5) {
            throw new RuntimeException("Invalid impression record: " + line);
        }

        ImpressionEvent event = new ImpressionEvent();
        event.timestampMicros = Long.parseLong(tokens[0]);
        event.campaignId = tokens[1];
        event.impressionId = tokens[2];
        event.userId = tokens[3];
        event.creativeId = tokens[4];
        return event;
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/campaignaudit/datatypes/ClickEvent.java
package campaignaudit.datatypes;

import java.io.Serializable;

public class ClickEvent implements Serializable {
    public long timestampMicros;
    public String campaignId;
    public String impressionId;
    public String clickId;
    public String quality;

    public ClickEvent() {
    }

    public static ClickEvent fromString(String line) {
        String[] tokens = line.split(",", -1);
        if (tokens.length != 5) {
            throw new RuntimeException("Invalid click record: " + line);
        }

        ClickEvent event = new ClickEvent();
        event.timestampMicros = Long.parseLong(tokens[0]);
        event.campaignId = tokens[1];
        event.impressionId = tokens[2];
        event.clickId = tokens[3];
        event.quality = tokens[4];
        return event;
    }

    public boolean isValid() {
        return "VALID".equals(quality);
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/campaignaudit/datatypes/AttributionOutcome.java
package campaignaudit.datatypes;

import java.io.Serializable;

public class AttributionOutcome implements Serializable {
    public String campaignId;
    public boolean attributed;
    public long lagMicros;

    public AttributionOutcome() {
    }

    public AttributionOutcome(String campaignId, boolean attributed, long lagMicros) {
        this.campaignId = campaignId;
        this.attributed = attributed;
        this.lagMicros = lagMicros;
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/campaignaudit/sources/BoundedImpressionSource.java
package campaignaudit.sources;

import campaignaudit.datatypes.ImpressionEvent;
import org.apache.flink.streaming.api.functions.source.RichParallelSourceFunction;
import org.apache.flink.streaming.api.watermark.Watermark;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.zip.GZIPInputStream;

public class BoundedImpressionSource extends RichParallelSourceFunction<ImpressionEvent> {
    private final String gzFilePath;
    private volatile boolean running = true;

    public BoundedImpressionSource(String gzFilePath) {
        this.gzFilePath = gzFilePath;
    }

    @Override
    public void run(SourceContext<ImpressionEvent> ctx) throws Exception {
        File file = new File(gzFilePath);
        if (!file.isFile()) {
            throw new IllegalArgumentException("Impression input must be a single .gz file: " + file.getAbsolutePath());
        }

        try (FileInputStream fis = new FileInputStream(file);
             GZIPInputStream gis = new GZIPInputStream(fis);
             BufferedReader reader = new BufferedReader(new InputStreamReader(gis, StandardCharsets.UTF_8))) {
            String line;
            while (running && (line = reader.readLine()) != null) {
                ImpressionEvent event = ImpressionEvent.fromString(line);
                synchronized (ctx.getCheckpointLock()) {
                    ctx.collectWithTimestamp(event, event.timestampMicros / 1000L);
                }
            }
        }

        synchronized (ctx.getCheckpointLock()) {
            ctx.emitWatermark(Watermark.MAX_WATERMARK);
        }
    }

    @Override
    public void cancel() {
        running = false;
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/campaignaudit/sources/BoundedClickSource.java
package campaignaudit.sources;

import campaignaudit.datatypes.ClickEvent;
import org.apache.flink.streaming.api.functions.source.RichParallelSourceFunction;
import org.apache.flink.streaming.api.watermark.Watermark;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.zip.GZIPInputStream;

public class BoundedClickSource extends RichParallelSourceFunction<ClickEvent> {
    private final String gzFilePath;
    private volatile boolean running = true;

    public BoundedClickSource(String gzFilePath) {
        this.gzFilePath = gzFilePath;
    }

    @Override
    public void run(SourceContext<ClickEvent> ctx) throws Exception {
        File file = new File(gzFilePath);
        if (!file.isFile()) {
            throw new IllegalArgumentException("Click input must be a single .gz file: " + file.getAbsolutePath());
        }

        try (FileInputStream fis = new FileInputStream(file);
             GZIPInputStream gis = new GZIPInputStream(fis);
             BufferedReader reader = new BufferedReader(new InputStreamReader(gis, StandardCharsets.UTF_8))) {
            String line;
            while (running && (line = reader.readLine()) != null) {
                ClickEvent event = ClickEvent.fromString(line);
                synchronized (ctx.getCheckpointLock()) {
                    ctx.collectWithTimestamp(event, event.timestampMicros / 1000L);
                }
            }
        }

        synchronized (ctx.getCheckpointLock()) {
            ctx.emitWatermark(Watermark.MAX_WATERMARK);
        }
    }

    @Override
    public void cancel() {
        running = false;
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/campaignaudit/sinks/OutputFileSink.java
package campaignaudit.sinks;

import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

public class OutputFileSink extends RichSinkFunction<String> {
    private final String outputPath;
    private transient BufferedWriter writer;

    public OutputFileSink(String outputPath) {
        this.outputPath = outputPath;
    }

    @Override
    public void open(Configuration parameters) throws IOException {
        File file = new File(outputPath);
        File parent = file.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        writer = new BufferedWriter(new FileWriter(file, false));
    }

    @Override
    public void invoke(String value, Context context) throws IOException {
        writer.write(value);
        writer.newLine();
    }

    @Override
    public void close() throws IOException {
        if (writer != null) {
            writer.flush();
            writer.close();
        }
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/campaignaudit/query/CampaignAttributionLagAudit.java
package campaignaudit.query;

import campaignaudit.datatypes.AttributionOutcome;
import campaignaudit.datatypes.ClickEvent;
import campaignaudit.datatypes.ImpressionEvent;
import campaignaudit.sinks.OutputFileSink;
import campaignaudit.sources.BoundedClickSource;
import campaignaudit.sources.BoundedImpressionSource;
import campaignaudit.utils.AppBase;
import org.apache.flink.api.common.state.ListState;
import org.apache.flink.api.common.state.ListStateDescriptor;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.common.typeinfo.Types;
import org.apache.flink.api.java.functions.KeySelector;
import org.apache.flink.api.java.utils.ParameterTool;
import org.apache.flink.streaming.api.datastream.ConnectedStreams;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.streaming.api.functions.co.KeyedCoProcessFunction;
import org.apache.flink.util.Collector;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class CampaignAttributionLagAudit extends AppBase {
    private static final long FINAL_TIMER = Long.MAX_VALUE - 1L;

    public static void main(String[] args) throws Exception {
        ParameterTool params = ParameterTool.fromArgs(args);
        String impressionInput = params.get("impression_input", null);
        String clickInput = params.get("click_input", null);
        String outputPath = params.get("output", null);

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(1);

        DataStream<ImpressionEvent> impressions = env
                .addSource(sourceOrTest(new BoundedImpressionSource(impressionInput), AppBase.impressions))
                .name("impressions");

        DataStream<ClickEvent> clicks = env
                .addSource(sourceOrTest(new BoundedClickSource(clickInput), AppBase.clicks))
                .name("clicks");

        ConnectedStreams<ImpressionEvent, ClickEvent> joinedInputs = impressions.connect(clicks);

        DataStream<AttributionOutcome> outcomes = joinedInputs
                .keyBy(new ImpressionKeySelector(), new ClickKeySelector())
                .process(new ImpressionClickJoiner())
                .name("join-impressions-and-clicks");

        DataStream<String> reportLines = outcomes
                .keyBy(outcome -> outcome.campaignId)
                .process(new CampaignAggregator())
                .name("campaign-report");

        reportLines
                .addSink(sinkOrTest(new OutputFileSink(outputPath)))
                .setParallelism(1)
                .name("file-output");

        env.execute("CampaignAttributionLagAudit");
    }

    private static class ImpressionKeySelector implements KeySelector<ImpressionEvent, String> {
        @Override
        public String getKey(ImpressionEvent value) {
            return value.campaignId + "|" + value.impressionId;
        }
    }

    private static class ClickKeySelector implements KeySelector<ClickEvent, String> {
        @Override
        public String getKey(ClickEvent value) {
            return value.campaignId + "|" + value.impressionId;
        }
    }

    private static class ImpressionClickJoiner extends KeyedCoProcessFunction<String, ImpressionEvent, ClickEvent, AttributionOutcome> {
        private ValueState<ImpressionEvent> impressionState;
        private ListState<Long> pendingValidClickTimes;
        private ValueState<Long> earliestValidClickTime;

        @Override
        public void open(org.apache.flink.configuration.Configuration parameters) {
            impressionState = getRuntimeContext().getState(new ValueStateDescriptor<>("impression", ImpressionEvent.class));
            pendingValidClickTimes = getRuntimeContext().getListState(new ListStateDescriptor<>("pending-valid-click-times", Types.LONG));
            earliestValidClickTime = getRuntimeContext().getState(new ValueStateDescriptor<>("earliest-valid-click-time", Types.LONG));
        }

        @Override
        public void processElement1(ImpressionEvent impression,
                                    Context ctx,
                                    Collector<AttributionOutcome> out) throws Exception {
            impressionState.update(impression);
            applyPendingClicks(impression);
            ctx.timerService().registerEventTimeTimer(FINAL_TIMER);
        }

        @Override
        public void processElement2(ClickEvent click,
                                    Context ctx,
                                    Collector<AttributionOutcome> out) throws Exception {
            if (!click.isValid()) {
                return;
            }

            ImpressionEvent impression = impressionState.value();
            if (impression == null) {
                List<Long> buffered = new ArrayList<>();
                for (Long timestamp : pendingValidClickTimes.get()) {
                    buffered.add(timestamp);
                }
                buffered.add(click.timestampMicros);
                pendingValidClickTimes.update(buffered);
            } else {
                considerClick(impression, click.timestampMicros);
            }
            ctx.timerService().registerEventTimeTimer(FINAL_TIMER);
        }

        @Override
        public void onTimer(long timestamp,
                            OnTimerContext ctx,
                            Collector<AttributionOutcome> out) throws Exception {
            if (timestamp != FINAL_TIMER) {
                return;
            }

            ImpressionEvent impression = impressionState.value();
            if (impression != null) {
                Long clickTime = earliestValidClickTime.value();
                if (clickTime == null) {
                    out.collect(new AttributionOutcome(impression.campaignId, false, -1L));
                } else {
                    out.collect(new AttributionOutcome(impression.campaignId, true, clickTime - impression.timestampMicros));
                }
            }

            impressionState.clear();
            pendingValidClickTimes.clear();
            earliestValidClickTime.clear();
        }

        private void applyPendingClicks(ImpressionEvent impression) throws Exception {
            for (Long clickTimestamp : pendingValidClickTimes.get()) {
                considerClick(impression, clickTimestamp);
            }
        }

        private void considerClick(ImpressionEvent impression, long clickTimestampMicros) throws Exception {
            if (clickTimestampMicros < impression.timestampMicros) {
                return;
            }

            Long current = earliestValidClickTime.value();
            if (current == null || clickTimestampMicros < current) {
                earliestValidClickTime.update(clickTimestampMicros);
            }
        }
    }

    private static class CampaignAggregator extends KeyedProcessFunction<String, AttributionOutcome, String> {
        private ValueState<Integer> unattributedCount;
        private ListState<Long> validLags;

        @Override
        public void open(org.apache.flink.configuration.Configuration parameters) {
            unattributedCount = getRuntimeContext().getState(new ValueStateDescriptor<>("unattributed-count", Types.INT));
            validLags = getRuntimeContext().getListState(new ListStateDescriptor<>("valid-lags", Types.LONG));
        }

        @Override
        public void processElement(AttributionOutcome value,
                                   Context ctx,
                                   Collector<String> out) throws Exception {
            Integer currentUnattributed = unattributedCount.value();
            if (currentUnattributed == null) {
                currentUnattributed = 0;
            }

            if (value.attributed) {
                List<Long> lags = new ArrayList<>();
                for (Long lag : validLags.get()) {
                    lags.add(lag);
                }
                lags.add(value.lagMicros);
                validLags.update(lags);
            } else {
                unattributedCount.update(currentUnattributed + 1);
            }

            ctx.timerService().registerEventTimeTimer(FINAL_TIMER);
        }

        @Override
        public void onTimer(long timestamp,
                            OnTimerContext ctx,
                            Collector<String> out) throws Exception {
            if (timestamp != FINAL_TIMER) {
                return;
            }

            List<Long> lags = new ArrayList<>();
            for (Long lag : validLags.get()) {
                lags.add(lag);
            }
            Collections.sort(lags);

            int unattributed = unattributedCount.value() == null ? 0 : unattributedCount.value();
            long p95 = -1L;
            if (!lags.isEmpty()) {
                int rank = (int) Math.ceil(lags.size() * 0.95d);
                p95 = lags.get(rank - 1);
            }

            out.collect(String.format(
                    "campaign=%s unattributed=%d p95_valid_click_lag_micros=%d",
                    ctx.getCurrentKey(),
                    unattributed,
                    p95));

            unattributedCount.clear();
            validLags.clear();
        }
    }
}
EOF

cd /app/workspace && mvn clean package -q
