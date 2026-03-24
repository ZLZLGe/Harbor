package com.example.reconciliation.client;

import java.util.List;

public record PageEnvelope<T>(
    List<T> items,
    String nextCursor,
    boolean hasMore
) {
}
