package com.acme.gateway.generated;

import com.google.protobuf.Empty;
import com.google.protobuf.Struct;
import io.grpc.MethodDescriptor;
import io.grpc.protobuf.ProtoUtils;
import io.grpc.stub.annotations.GrpcGenerated;
import io.grpc.stub.annotations.RpcMethod;

@GrpcGenerated
public final class InventoryGatewayGrpc {
    public static final String SERVICE_NAME = "gateway.inventory.v1.InventoryGateway";

    private static volatile MethodDescriptor<Empty, Struct> describeRouteMethod;

    private InventoryGatewayGrpc() {
    }

    @RpcMethod(
        fullMethodName = SERVICE_NAME + '/' + "DescribeRoute",
        requestType = Empty.class,
        responseType = Struct.class,
        methodType = MethodDescriptor.MethodType.UNARY)
    public static MethodDescriptor<Empty, Struct> getDescribeRouteMethod() {
        MethodDescriptor<Empty, Struct> local = describeRouteMethod;
        if (local == null) {
            synchronized (InventoryGatewayGrpc.class) {
                local = describeRouteMethod;
                if (local == null) {
                    local = MethodDescriptor.<Empty, Struct>newBuilder()
                        .setType(MethodDescriptor.MethodType.UNARY)
                        .setFullMethodName(MethodDescriptor.generateFullMethodName(SERVICE_NAME, "DescribeRoute"))
                        .setSampledToLocalTracing(true)
                        .setRequestMarshaller(ProtoUtils.marshaller(Empty.getDefaultInstance()))
                        .setResponseMarshaller(ProtoUtils.marshaller(Struct.getDefaultInstance()))
                        .build();
                    describeRouteMethod = local;
                }
            }
        }
        return local;
    }
}
