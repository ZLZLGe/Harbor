import os
import subprocess
import textwrap
from pathlib import Path


APP_HOME = Path(os.getenv("APP_HOME", "/workspace/order-analytics"))
TARGET_FILE = APP_HOME / "src/main/java/com/acme/analytics/reporting/OrderSummaryQueryService.java"

VALIDATOR_SOURCE = textwrap.dedent(
    """
    import com.acme.analytics.reporting.OrderSummaryQueryService;
    import com.acme.analytics.reporting.OrderSummaryQueryService.CustomerRepository;
    import com.acme.analytics.reporting.OrderSummaryQueryService.OrderMetrics;
    import com.acme.analytics.reporting.OrderSummaryQueryService.OrderRecord;
    import com.acme.analytics.reporting.OrderSummaryQueryService.OrderRepository;
    import com.acme.analytics.reporting.OrderSummaryQueryService.OrderSummaryResponse;
    import com.acme.analytics.reporting.OrderSummaryQueryService.OrderSummaryRow;
    import com.acme.analytics.reporting.OrderSummaryQueryService.ShipmentRepository;
    import com.acme.analytics.reporting.OrderSummaryQueryService.ShipmentSnapshot;

    import java.time.LocalDate;
    import java.util.Collection;
    import java.util.HashMap;
    import java.util.List;
    import java.util.Map;

    public class OrderSummaryValidator {
        public static void main(String[] args) {
            List<OrderRecord> orders = List.of(
                new OrderRecord(501L, 9001L, "SO-501", LocalDate.parse("2026-02-01"), 12000L),
                new OrderRecord(502L, 9002L, "SO-502", LocalDate.parse("2026-02-02"), 24000L),
                new OrderRecord(503L, 9001L, "SO-503", LocalDate.parse("2026-02-03"), 5000L)
            );

            Map<Long, OrderMetrics> metrics = Map.of(
                501L, new OrderMetrics(3, 1500L, 0L),
                502L, new OrderMetrics(5, 2000L, 3000L),
                503L, new OrderMetrics(1, 0L, 0L)
            );

            Map<Long, String> customerTiers = Map.of(
                9001L, "VIP",
                9002L, "STANDARD"
            );

            Map<Long, ShipmentSnapshot> shipments = Map.of(
                501L, new ShipmentSnapshot("DELIVERED"),
                502L, new ShipmentSnapshot("IN_TRANSIT")
            );

            CountingOrderRepository orderRepository = new CountingOrderRepository(orders, metrics);
            CountingCustomerRepository customerRepository = new CountingCustomerRepository(customerTiers);
            CountingShipmentRepository shipmentRepository = new CountingShipmentRepository(shipments);

            OrderSummaryQueryService service = new OrderSummaryQueryService(
                orderRepository,
                customerRepository,
                shipmentRepository
            );

            OrderSummaryResponse response = service.fetchOrderSummaries(
                LocalDate.parse("2026-02-01"),
                LocalDate.parse("2026-02-28"),
                3
            );

            require(response.rows().size() == 3, "expected 3 rows");

            OrderSummaryRow first = response.rows().get(0);
            require(first.orderId() == 501L, "unexpected first order id");
            require("VIP".equals(first.customerTier()), "unexpected first customer tier");
            require(first.lineItemCount() == 3, "unexpected first line item count");
            require(first.discountCents() == 1500L, "unexpected first discount");
            require(first.refundedCents() == 0L, "unexpected first refund");
            require("DELIVERED".equals(first.shipmentStatus()), "unexpected first shipment status");

            OrderSummaryRow third = response.rows().get(2);
            require("PENDING".equals(third.shipmentStatus()), "missing shipment should map to PENDING");

            require(response.totals().orderCount() == 3, "unexpected order count total");
            require(response.totals().grossRevenueCents() == 41000L, "unexpected gross total");
            require(response.totals().refundedCents() == 3000L, "unexpected refunded total");
            require(response.totals().shippedOrderCount() == 1, "unexpected shipped total");

            require(orderRepository.findRecentOrdersCalls == 1, "findRecentOrders should be called once");
            require(orderRepository.findOrderMetricsCalls == 1, "findOrderMetrics should be called once");
            require(orderRepository.countLineItemsCalls == 0, "countLineItems should not be called per order");
            require(orderRepository.sumDiscountCalls == 0, "sumDiscountCents should not be called per order");
            require(orderRepository.sumRefundedCalls == 0, "sumRefundedCents should not be called per order");

            require(customerRepository.findCustomerTiersCalls == 1, "findCustomerTiers should be called once");
            require(customerRepository.findCustomerTierCalls == 0, "findCustomerTier should not be called per order");

            require(shipmentRepository.findLatestShipmentsCalls == 1, "findLatestShipments should be called once");
            require(shipmentRepository.findLatestShipmentCalls == 0, "findLatestShipment should not be called per order");

            System.out.println("VALIDATION_OK");
        }

        private static void require(boolean condition, String message) {
            if (!condition) {
                throw new IllegalStateException(message);
            }
        }

        private static final class CountingOrderRepository implements OrderRepository {
            private final List<OrderRecord> orders;
            private final Map<Long, OrderMetrics> metricsByOrderId;

            private int findRecentOrdersCalls;
            private int countLineItemsCalls;
            private int sumDiscountCalls;
            private int sumRefundedCalls;
            private int findOrderMetricsCalls;

            private CountingOrderRepository(List<OrderRecord> orders, Map<Long, OrderMetrics> metricsByOrderId) {
                this.orders = orders;
                this.metricsByOrderId = metricsByOrderId;
            }

            @Override
            public List<OrderRecord> findRecentOrders(LocalDate startDate, LocalDate endDate, int limit) {
                findRecentOrdersCalls++;
                return orders;
            }

            @Override
            public int countLineItems(long orderId) {
                countLineItemsCalls++;
                return metricsByOrderId.get(orderId).lineItemCount();
            }

            @Override
            public long sumDiscountCents(long orderId) {
                sumDiscountCalls++;
                return metricsByOrderId.get(orderId).discountCents();
            }

            @Override
            public long sumRefundedCents(long orderId) {
                sumRefundedCalls++;
                return metricsByOrderId.get(orderId).refundedCents();
            }

            @Override
            public Map<Long, OrderMetrics> findOrderMetrics(Collection<Long> orderIds) {
                findOrderMetricsCalls++;
                Map<Long, OrderMetrics> result = new HashMap<>();
                for (Long orderId : orderIds) {
                    result.put(orderId, metricsByOrderId.get(orderId));
                }
                return result;
            }
        }

        private static final class CountingCustomerRepository implements CustomerRepository {
            private final Map<Long, String> customerTierById;

            private int findCustomerTierCalls;
            private int findCustomerTiersCalls;

            private CountingCustomerRepository(Map<Long, String> customerTierById) {
                this.customerTierById = customerTierById;
            }

            @Override
            public String findCustomerTier(long customerId) {
                findCustomerTierCalls++;
                return customerTierById.get(customerId);
            }

            @Override
            public Map<Long, String> findCustomerTiers(Collection<Long> customerIds) {
                findCustomerTiersCalls++;
                Map<Long, String> result = new HashMap<>();
                for (Long customerId : customerIds) {
                    String tier = customerTierById.get(customerId);
                    if (tier != null) {
                        result.put(customerId, tier);
                    }
                }
                return result;
            }
        }

        private static final class CountingShipmentRepository implements ShipmentRepository {
            private final Map<Long, ShipmentSnapshot> shipmentByOrderId;

            private int findLatestShipmentCalls;
            private int findLatestShipmentsCalls;

            private CountingShipmentRepository(Map<Long, ShipmentSnapshot> shipmentByOrderId) {
                this.shipmentByOrderId = shipmentByOrderId;
            }

            @Override
            public ShipmentSnapshot findLatestShipment(long orderId) {
                findLatestShipmentCalls++;
                return shipmentByOrderId.getOrDefault(orderId, ShipmentSnapshot.PENDING);
            }

            @Override
            public Map<Long, ShipmentSnapshot> findLatestShipments(Collection<Long> orderIds) {
                findLatestShipmentsCalls++;
                Map<Long, ShipmentSnapshot> result = new HashMap<>();
                for (Long orderId : orderIds) {
                    ShipmentSnapshot shipment = shipmentByOrderId.get(orderId);
                    if (shipment != null) {
                        result.put(orderId, shipment);
                    }
                }
                return result;
            }
        }
    }
    """
)


def run(cmd, cwd=APP_HOME, timeout=120):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_primary_output_file_present():
    assert TARGET_FILE.exists(), f"missing primary output file: {TARGET_FILE}"
    text = TARGET_FILE.read_text()
    assert "class OrderSummaryQueryService" in text
    assert "fetchOrderSummaries" in text


def test_service_moves_to_batch_queries():
    text = TARGET_FILE.read_text()
    assert "findOrderMetrics" in text
    assert "findCustomerTiers" in text
    assert "findLatestShipments" in text
    assert "countLineItems(order.orderId())" not in text
    assert "sumDiscountCents(order.orderId())" not in text
    assert "sumRefundedCents(order.orderId())" not in text
    assert "findCustomerTier(order.customerId())" not in text
    assert "findLatestShipment(order.orderId())" not in text


def test_project_builds():
    run(["mvn", "-q", "-DskipTests", "package"])
    compiled = APP_HOME / "target/classes/com/acme/analytics/reporting/OrderSummaryQueryService.class"
    assert compiled.exists(), f"compiled class missing: {compiled}"


def test_contract_and_query_count():
    run(["mvn", "-q", "-DskipTests", "package"])

    validator_dir = Path("/tmp/order-analytics-validator")
    validator_dir.mkdir(parents=True, exist_ok=True)
    validator_java = validator_dir / "OrderSummaryValidator.java"
    validator_java.write_text(VALIDATOR_SOURCE)

    run(["javac", "-cp", f"{APP_HOME}/target/classes", str(validator_java)], cwd=validator_dir)
    result = run(
        ["java", "-cp", f"{APP_HOME}/target/classes:{validator_dir}", "OrderSummaryValidator"],
        cwd=validator_dir,
    )

    assert "VALIDATION_OK" in result.stdout, result.stdout + result.stderr
