package com.acme.release;

public final class BulletinApplication {
    private BulletinApplication() {
    }

    public static String headline() {
        return "release-bulletin-service";
    }

    public static void main(String[] args) {
        System.out.println(headline());
    }
}
