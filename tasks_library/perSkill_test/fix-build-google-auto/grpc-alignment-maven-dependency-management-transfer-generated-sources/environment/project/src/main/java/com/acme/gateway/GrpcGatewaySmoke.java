package com.acme.gateway;

import com.acme.gateway.generated.InventoryBridgeProto;
import com.acme.gateway.generated.InventoryGatewayGrpc;
import com.google.protobuf.Empty;
import com.google.protobuf.Struct;
import com.google.type.Date;
import io.grpc.MethodDescriptor;

public final class GrpcGatewaySmoke {
    public String renderGeneratedRoute() throws Exception {
        return InventoryBridgeProto.schemaJson();
    }

    public String methodName() {
        MethodDescriptor<Empty, Struct> method = InventoryGatewayGrpc.getDescribeRouteMethod();
        return method.getFullMethodName();
    }

    public String releaseTag() {
        Date releaseDate = Date.newBuilder()
            .setYear(2026)
            .setMonth(3)
            .setDay(25)
            .build();
        return releaseDate.getYear() + "-" + releaseDate.getMonth() + "-" + releaseDate.getDay();
    }
}
