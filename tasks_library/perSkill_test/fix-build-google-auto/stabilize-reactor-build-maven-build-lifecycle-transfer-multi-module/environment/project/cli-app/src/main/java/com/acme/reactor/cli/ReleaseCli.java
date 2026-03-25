package com.acme.reactor.cli;

import com.acme.reactor.service.RolloutPlanner;

public final class ReleaseCli {
    private ReleaseCli() {
    }

    public static String buildLine() {
        return "PLAN: " + new RolloutPlanner().renderPlan();
    }

    public static void main(String[] args) {
        System.out.println(buildLine());
    }
}
