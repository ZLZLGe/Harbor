package com.example.catalog.api;

import com.example.catalog.model.CatalogItem;
import com.example.catalog.model.CatalogPreview;
import com.example.catalog.model.CatalogPreviewRequest;
import com.example.catalog.model.CatalogSnapshot;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import javax.annotation.PostConstruct;
import javax.ws.rs.Consumes;
import javax.ws.rs.GET;
import javax.ws.rs.POST;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.MediaType;

@Path("/catalog")
@Produces({MediaType.APPLICATION_JSON, MediaType.APPLICATION_XML})
@Consumes({MediaType.APPLICATION_JSON, MediaType.APPLICATION_XML})
public class CatalogResource {

    private final List<CatalogItem> seededItems = new ArrayList<>();

    @PostConstruct
    public void seedCatalog() {
        seededItems.clear();
        seededItems.add(new CatalogItem("SKU-100", "Trail Mix", "snack-box", "A1"));
        seededItems.add(new CatalogItem("SKU-200", "Travel Kettle", "beverage-kit", "B4"));
    }

    @GET
    @Path("/summary")
    public CatalogSnapshot summary() {
        return new CatalogSnapshot("seasonal-catalog", "ops-bot", seededItems);
    }

    @POST
    @Path("/preview")
    public CatalogPreview preview(CatalogPreviewRequest request) {
        String trimmedName = request.getDisplayName().trim();
        String zone = request.getWarehouseZone() == null || request.getWarehouseZone().isBlank()
            ? "UNASSIGNED"
            : request.getWarehouseZone().trim().toUpperCase(Locale.ROOT);
        return new CatalogPreview(
            request.getSku(),
            trimmedName,
            zone,
            "READY",
            toSlug(request.getSku(), trimmedName),
            "catalog-preview"
        );
    }

    private String toSlug(String sku, String displayName) {
        String normalizedName = displayName
            .trim()
            .toLowerCase(Locale.ROOT)
            .replaceAll("[^a-z0-9]+", "-")
            .replaceAll("^-|-$", "");
        return sku.toLowerCase(Locale.ROOT) + "-" + normalizedName;
    }
}
