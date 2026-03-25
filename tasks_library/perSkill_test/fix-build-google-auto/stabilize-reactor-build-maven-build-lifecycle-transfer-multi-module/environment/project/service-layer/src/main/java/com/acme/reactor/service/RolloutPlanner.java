package com.acme.reactor.service;

import com.acme.reactor.shared.ReleaseCatalog;

public final class RolloutPlanner {
    public String renderPlan() {
        return ReleaseCatalog.releaseName() + "|" + String.join(">", ReleaseCatalog.orderedStages());
    }
}
