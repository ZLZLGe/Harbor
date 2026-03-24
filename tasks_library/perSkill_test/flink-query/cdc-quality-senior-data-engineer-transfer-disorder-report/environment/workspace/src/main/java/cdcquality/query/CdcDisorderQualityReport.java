package cdcquality.query;

import cdcquality.utils.AppBase;
import org.apache.flink.api.java.utils.ParameterTool;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

public class CdcDisorderQualityReport extends AppBase {

    public static void main(String[] args) throws Exception {
        ParameterTool params = ParameterTool.fromArgs(args);
        String cdcInput = params.get("cdc_input", null);
        String outputPath = params.get("output", null);

        System.out.println("cdc_input  " + cdcInput);
        System.out.println("output  " + outputPath);

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // TODO: implement the CDC quality report pipeline.

        env.execute("CdcDisorderQualityReport");
    }
}
