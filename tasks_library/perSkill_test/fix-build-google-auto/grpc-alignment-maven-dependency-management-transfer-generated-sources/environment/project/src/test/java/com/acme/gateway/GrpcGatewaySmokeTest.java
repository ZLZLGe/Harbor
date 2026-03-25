package com.acme.gateway;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class GrpcGatewaySmokeTest {
    @Test
    void generatedSourcesCompileIntoTheSmokePath() throws Exception {
        GrpcGatewaySmoke smoke = new GrpcGatewaySmoke();

        assertEquals("{\"route\":\"inventory.v1.Items\",\"transport\":\"grpc\"}", smoke.renderGeneratedRoute());
        assertEquals("gateway.inventory.v1.InventoryGateway/DescribeRoute", smoke.methodName());
        assertEquals("2026-3-25", smoke.releaseTag());
    }
}
