package com.example.catalog.api;

import com.example.catalog.model.CatalogPreview;
import com.example.catalog.model.CatalogPreviewRequest;
import com.example.catalog.model.CatalogSnapshot;
import java.util.List;
import javax.ws.rs.client.Entity;
import javax.ws.rs.core.Application;
import javax.ws.rs.core.MediaType;
import org.glassfish.jersey.test.JerseyTest;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class CatalogResourceTest extends JerseyTest {

    @Override
    protected Application configure() {
        return new CatalogApplication();
    }

    @Test
    void summaryEndpointReturnsSeededCatalog() {
        CatalogSnapshot snapshot = target("catalog/summary")
            .request(MediaType.APPLICATION_JSON_TYPE)
            .get(CatalogSnapshot.class);

        assertEquals("seasonal-catalog", snapshot.getCatalogName());
        assertEquals("ops-bot", snapshot.getMaintainer());
        assertEquals(2, snapshot.getItemCount());
        assertEquals(List.of("SKU-100", "SKU-200"), snapshot.getItems().stream().map(item -> item.getSku()).toList());
    }

    @Test
    void previewEndpointNormalizesXmlRequest() {
        CatalogPreview preview = target("catalog/preview")
            .request(MediaType.APPLICATION_XML_TYPE)
            .post(
                Entity.entity(
                    new CatalogPreviewRequest("sku-300", "  Insulated Mug  ", " c7 "),
                    MediaType.APPLICATION_XML_TYPE
                ),
                CatalogPreview.class
            );

        assertEquals("Insulated Mug", preview.getDisplayName());
        assertEquals("C7", preview.getWarehouseZone());
        assertEquals("READY", preview.getStatus());
        assertEquals("catalog-preview", preview.getGeneratedBy());
        assertEquals("sku-300-insulated-mug", preview.getSlug());
    }

    @Test
    void previewEndpointFallsBackToUnassignedZone() {
        CatalogPreview preview = target("catalog/preview")
            .request(MediaType.APPLICATION_JSON_TYPE)
            .post(
                Entity.entity(
                    new CatalogPreviewRequest("sku-410", "Desk Lamp", "   "),
                    MediaType.APPLICATION_JSON_TYPE
                ),
                CatalogPreview.class
            );

        assertEquals("UNASSIGNED", preview.getWarehouseZone());
        assertEquals("sku-410-desk-lamp", preview.getSlug());
    }
}
