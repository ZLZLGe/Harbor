package campaignaudit.utils;

import org.apache.flink.streaming.api.functions.sink.SinkFunction;
import org.apache.flink.streaming.api.functions.source.SourceFunction;

public class AppBase {
    public static SourceFunction<?> impressions = null;
    public static SourceFunction<?> clicks = null;
    public static SinkFunction<?> out = null;

    @SuppressWarnings("unchecked")
    public static <T> SourceFunction<T> sourceOrTest(SourceFunction<T> source, SourceFunction<?> override) {
        if (override == null) {
            return source;
        }
        return (SourceFunction<T>) override;
    }

    @SuppressWarnings("unchecked")
    public static <T> SinkFunction<T> sinkOrTest(SinkFunction<T> sink) {
        if (out == null) {
            return sink;
        }
        return (SinkFunction<T>) out;
    }
}
