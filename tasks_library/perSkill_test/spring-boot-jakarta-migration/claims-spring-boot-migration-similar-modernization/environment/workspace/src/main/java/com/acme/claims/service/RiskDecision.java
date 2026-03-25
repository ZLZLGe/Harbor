package com.acme.claims.service;

public class RiskDecision {

    private int score;
    private boolean manualReviewRequired;

    public RiskDecision() {
    }

    public RiskDecision(int score, boolean manualReviewRequired) {
        this.score = score;
        this.manualReviewRequired = manualReviewRequired;
    }

    public int getScore() {
        return score;
    }

    public void setScore(int score) {
        this.score = score;
    }

    public boolean isManualReviewRequired() {
        return manualReviewRequired;
    }

    public void setManualReviewRequired(boolean manualReviewRequired) {
        this.manualReviewRequired = manualReviewRequired;
    }
}
