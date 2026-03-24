#!/bin/bash

set -euo pipefail

mkdir -p /app/workspace/src/main/java/pipelinesla/query
mkdir -p /app/workspace/src/main/java/pipelinesla/utils
mkdir -p /app/workspace/src/main/java/pipelinesla/datatypes

cat <<'EOF' > /app/workspace/src/main/java/pipelinesla/datatypes/PipelineTaskEvent.java
package pipelinesla.datatypes;

import java.io.Serializable;
import java.time.Instant;

public class PipelineTaskEvent implements Serializable {
    public long eventTimeMicros;
    public String pipelineId;
    public String taskId;
    public String eventType;

    public static PipelineTaskEvent fromCsv(String line) {
        String[] parts = line.split(",", -1);
        if (parts.length < 4) {
            throw new IllegalArgumentException("Invalid lifecycle record: " + line);
        }

        PipelineTaskEvent event = new PipelineTaskEvent();
        event.eventTimeMicros = Instant.parse(parts[0]).toEpochMilli() * 1000L;
        event.pipelineId = parts[1];
        event.taskId = parts[2];
        event.eventType = parts[3];
        return event;
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/pipelinesla/datatypes/PipelineCloseEvent.java
package pipelinesla.datatypes;

import java.io.Serializable;
import java.time.Instant;

public class PipelineCloseEvent implements Serializable {
    public long closeTimeMicros;
    public String pipelineId;

    public static PipelineCloseEvent fromCsv(String line) {
        String[] parts = line.split(",", -1);
        if (parts.length < 2) {
            throw new IllegalArgumentException("Invalid close record: " + line);
        }

        PipelineCloseEvent event = new PipelineCloseEvent();
        event.closeTimeMicros = Instant.parse(parts[0]).toEpochMilli() * 1000L;
        event.pipelineId = parts[1];
        return event;
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/pipelinesla/utils/AppBase.java
package pipelinesla.utils;

import org.apache.flink.api.java.utils.ParameterTool;

public abstract class AppBase {
    protected static ParameterTool parseArgs(String[] args) {
        return ParameterTool.fromArgs(args);
    }
}
EOF

cat <<'EOF' > /app/workspace/src/main/java/pipelinesla/query/PipelineCloseoutSlaRollup.java
package pipelinesla.query;

import pipelinesla.datatypes.PipelineCloseEvent;
import pipelinesla.datatypes.PipelineTaskEvent;
import pipelinesla.utils.AppBase;
import org.apache.flink.api.java.utils.ParameterTool;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.zip.GZIPInputStream;

public class PipelineCloseoutSlaRollup extends AppBase {

    public static void main(String[] args) throws Exception {
        ParameterTool params = parseArgs(args);
        String taskInput = params.getRequired("task_input");
        String closeInput = params.getRequired("close_input");
        String outputPath = params.getRequired("output");

        List<PipelineTaskEvent> taskEvents = readTaskEvents(taskInput);
        List<PipelineCloseEvent> closeEvents = readCloseEvents(closeInput);

        Map<String, Long> closeTimes = new HashMap<>();
        for (PipelineCloseEvent closeEvent : closeEvents) {
            closeTimes.merge(
                    closeEvent.pipelineId,
                    closeEvent.closeTimeMicros,
                    Math::min);
        }

        Map<String, List<PipelineTaskEvent>> tasksByPipeline = new HashMap<>();
        for (PipelineTaskEvent taskEvent : taskEvents) {
            tasksByPipeline
                    .computeIfAbsent(taskEvent.pipelineId, ignored -> new ArrayList<>())
                    .add(taskEvent);
        }

        Map<String, PipelineSummary> results = new TreeMap<>();
        for (Map.Entry<String, Long> entry : closeTimes.entrySet()) {
            String pipelineId = entry.getKey();
            long closeTimeMicros = entry.getValue();
            List<PipelineTaskEvent> lifecycle = tasksByPipeline.getOrDefault(pipelineId, List.of());
            lifecycle.sort(Comparator.comparingLong(event -> event.eventTimeMicros));
            results.put(pipelineId, summarizePipeline(lifecycle, closeTimeMicros));
        }

        List<String> outputLines = new ArrayList<>();
        for (Map.Entry<String, PipelineSummary> entry : results.entrySet()) {
            PipelineSummary summary = entry.getValue();
            outputLines.add(
                    "pipeline=" + entry.getKey()
                            + " longest_backlog_micros=" + summary.longestBacklogMicros
                            + " backlog_task_count=" + summary.backlogTaskCount
                            + " failed_task_count=" + summary.failedTaskCount);
        }

        Path output = Path.of(outputPath);
        if (output.getParent() != null) {
            Files.createDirectories(output.getParent());
        }
        Files.write(output, outputLines, StandardCharsets.UTF_8);
    }

    private static PipelineSummary summarizePipeline(List<PipelineTaskEvent> lifecycle, long closeTimeMicros) {
        Set<String> blockedTasks = new HashSet<>();
        Set<String> currentIntervalTasks = new HashSet<>();
        Set<String> failedTasks = new HashSet<>();

        long currentIntervalStart = -1L;
        long bestStart = -1L;
        long bestDuration = 0L;
        int bestTaskCount = 0;

        for (PipelineTaskEvent event : lifecycle) {
            if (event.eventTimeMicros > closeTimeMicros) {
                continue;
            }

            if ("FAILED".equals(event.eventType)) {
                failedTasks.add(event.taskId);
                if (blockedTasks.remove(event.taskId) && blockedTasks.isEmpty()) {
                    IntervalChoice choice = chooseInterval(
                            currentIntervalStart,
                            event.eventTimeMicros,
                            currentIntervalTasks.size(),
                            bestStart,
                            bestDuration,
                            bestTaskCount);
                    bestStart = choice.bestStart;
                    bestDuration = choice.bestDuration;
                    bestTaskCount = choice.bestTaskCount;
                    currentIntervalStart = -1L;
                    currentIntervalTasks = new HashSet<>();
                }
                continue;
            }

            if ("READY".equals(event.eventType)) {
                if (blockedTasks.remove(event.taskId) && blockedTasks.isEmpty()) {
                    IntervalChoice choice = chooseInterval(
                            currentIntervalStart,
                            event.eventTimeMicros,
                            currentIntervalTasks.size(),
                            bestStart,
                            bestDuration,
                            bestTaskCount);
                    bestStart = choice.bestStart;
                    bestDuration = choice.bestDuration;
                    bestTaskCount = choice.bestTaskCount;
                    currentIntervalStart = -1L;
                    currentIntervalTasks = new HashSet<>();
                }
                continue;
            }

            if ("BLOCKED".equals(event.eventType)) {
                if (blockedTasks.isEmpty()) {
                    currentIntervalStart = event.eventTimeMicros;
                    currentIntervalTasks = new HashSet<>();
                }
                if (blockedTasks.add(event.taskId)) {
                    currentIntervalTasks.add(event.taskId);
                }
            }
        }

        if (!blockedTasks.isEmpty()) {
            IntervalChoice choice = chooseInterval(
                    currentIntervalStart,
                    closeTimeMicros,
                    currentIntervalTasks.size(),
                    bestStart,
                    bestDuration,
                    bestTaskCount);
            bestDuration = choice.bestDuration;
            bestTaskCount = choice.bestTaskCount;
        }

        PipelineSummary summary = new PipelineSummary();
        summary.longestBacklogMicros = bestDuration;
        summary.backlogTaskCount = bestTaskCount;
        summary.failedTaskCount = failedTasks.size();
        return summary;
    }

    private static IntervalChoice chooseInterval(
            long startMicros,
            long endMicros,
            int taskCount,
            long currentBestStart,
            long currentBestDuration,
            int currentBestTaskCount) {
        long duration = Math.max(0L, endMicros - startMicros);
        if (startMicros < 0L) {
            return new IntervalChoice(currentBestStart, currentBestDuration, currentBestTaskCount);
        }
        if (duration > currentBestDuration) {
            return new IntervalChoice(startMicros, duration, taskCount);
        }
        if (duration == currentBestDuration && (currentBestStart < 0L || startMicros < currentBestStart)) {
            return new IntervalChoice(startMicros, duration, taskCount);
        }
        return new IntervalChoice(currentBestStart, currentBestDuration, currentBestTaskCount);
    }

    private static List<PipelineTaskEvent> readTaskEvents(String path) throws Exception {
        List<PipelineTaskEvent> events = new ArrayList<>();
        try (FileInputStream fis = new FileInputStream(path);
             GZIPInputStream gis = new GZIPInputStream(fis);
             InputStreamReader isr = new InputStreamReader(gis, StandardCharsets.UTF_8);
             BufferedReader reader = new BufferedReader(isr)) {
            String line;
            boolean firstLine = true;
            while ((line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) {
                    continue;
                }
                if (firstLine) {
                    firstLine = false;
                    if (line.startsWith("event_time_utc")) {
                        continue;
                    }
                }
                events.add(PipelineTaskEvent.fromCsv(line));
            }
        }
        return events;
    }

    private static List<PipelineCloseEvent> readCloseEvents(String path) throws Exception {
        List<PipelineCloseEvent> events = new ArrayList<>();
        try (FileInputStream fis = new FileInputStream(path);
             GZIPInputStream gis = new GZIPInputStream(fis);
             InputStreamReader isr = new InputStreamReader(gis, StandardCharsets.UTF_8);
             BufferedReader reader = new BufferedReader(isr)) {
            String line;
            boolean firstLine = true;
            while ((line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) {
                    continue;
                }
                if (firstLine) {
                    firstLine = false;
                    if (line.startsWith("close_time_utc")) {
                        continue;
                    }
                }
                events.add(PipelineCloseEvent.fromCsv(line));
            }
        }
        return events;
    }

    public static class PipelineSummary {
        public long longestBacklogMicros;
        public int backlogTaskCount;
        public int failedTaskCount;
    }

    public static class IntervalChoice {
        public long bestStart;
        public long bestDuration;
        public int bestTaskCount;

        public IntervalChoice(long bestStart, long bestDuration, int bestTaskCount) {
            this.bestStart = bestStart;
            this.bestDuration = bestDuration;
            this.bestTaskCount = bestTaskCount;
        }
    }
}
EOF
