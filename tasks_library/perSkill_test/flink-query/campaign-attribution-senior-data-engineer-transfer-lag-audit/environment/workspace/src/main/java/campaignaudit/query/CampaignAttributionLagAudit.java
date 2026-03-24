package campaignaudit.query;

import campaignaudit.utils.AppBase;
import org.apache.flink.api.java.utils.ParameterTool;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

public class CampaignAttributionLagAudit extends AppBase {

    public static void main(String[] args) throws Exception {
        ParameterTool params = ParameterTool.fromArgs(args);
        String impressionInput = params.get("impression_input", null);
        String clickInput = params.get("click_input", null);
        String outputPath = params.get("output", null);

        System.out.println("impression_input  " + impressionInput);
        System.out.println("click_input  " + clickInput);
        System.out.println("output  " + outputPath);

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // TODO: implement the campaign attribution lag audit pipeline.

        env.execute("CampaignAttributionLagAudit");
    }
}
