package com.example.catalog.api;

import javax.ws.rs.ApplicationPath;
import org.glassfish.jersey.server.ResourceConfig;

@ApplicationPath("/")
public class CatalogApplication extends ResourceConfig {

    public CatalogApplication() {
        register(CatalogResource.class);
    }
}
