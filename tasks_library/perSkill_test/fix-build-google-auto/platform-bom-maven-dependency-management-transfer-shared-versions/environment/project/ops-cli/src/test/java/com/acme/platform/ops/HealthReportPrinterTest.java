package com.acme.platform.ops;

import org.junit.Assert;
import org.junit.Test;

public class HealthReportPrinterTest {
    @Test
    public void rendersStructuredJson() {
        HealthReportPrinter printer = new HealthReportPrinter();

        String json = printer.render("scheduler", true);

        Assert.assertTrue(json.contains("\"service\":\"scheduler\""));
        Assert.assertTrue(json.contains("\"healthy\":true"));
    }
}
