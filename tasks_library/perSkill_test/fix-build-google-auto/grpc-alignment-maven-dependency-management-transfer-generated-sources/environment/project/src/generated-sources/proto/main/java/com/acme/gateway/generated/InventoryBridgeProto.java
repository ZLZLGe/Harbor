package com.acme.gateway.generated;

import com.google.protobuf.RuntimeVersion;
import com.google.protobuf.Struct;
import com.google.protobuf.Value;
import com.google.protobuf.util.JsonFormat;

public final class InventoryBridgeProto {
    static {
        RuntimeVersion.validateProtobufGencodeVersion(
            RuntimeVersion.RuntimeDomain.PUBLIC,
            4,
            29,
            0,
            "",
            InventoryBridgeProto.class.getName());
    }

    private InventoryBridgeProto() {
    }

    public static String schemaJson() throws Exception {
        Struct payload = Struct.newBuilder()
            .putFields("route", Value.newBuilder().setStringValue("inventory.v1.Items").build())
            .putFields("transport", Value.newBuilder().setStringValue("grpc").build())
            .build();
        return JsonFormat.printer().omittingInsignificantWhitespace().print(payload);
    }
}
