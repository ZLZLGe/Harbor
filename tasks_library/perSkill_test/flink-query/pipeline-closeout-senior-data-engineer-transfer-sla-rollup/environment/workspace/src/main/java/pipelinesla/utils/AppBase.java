package pipelinesla.utils;

import org.apache.flink.api.java.utils.ParameterTool;

public abstract class AppBase {
    protected static ParameterTool parseArgs(String[] args) {
        return ParameterTool.fromArgs(args);
    }
}
