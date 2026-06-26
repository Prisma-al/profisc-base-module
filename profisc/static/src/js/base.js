/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { useService } from "@web/core/utils/hooks";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.bus_service = useService("bus_service");
    },

    async onClickSendOrder() {
        const order = this.pos.get_order();
        if (!order || order.is_empty()) {
            console.warn("No active order found or order is empty");
            return;
        }

        if (this.pos.config.module_pos_restaurant) {
            try {
                console.log("Sending order to Kitchen Display only...");

                order.is_draft = true;
                order.sent_fiscal = false; // Don't fiscalize kitchen orders
                await this.pos.sendOrderInPreparationUpdateLastChange(order);

                const orderLines = order.get_orderlines?.() || [];
                const lines = orderLines
                    .map(line => ({
                        product_id: line.product_id?.id || null,
                        qty: Number(line.qty || 0),
                        note: String(line.note || ""),
                        name: String(line.full_product_name || line.product_id?.display_name || ""),
                    }))
                    .filter(l => l.product_id !== null && l.qty > 0);

                if (!lines.length) {
                    console.warn("No valid order lines to send to Kitchen Display");
                    return;
                }


                const orderData = {
                    id: order.backendId || order.name || "",
                    name: order.name || "",
                    pos_config_id: this.pos.config.id || 0,
                    table_id: order.table?.id || null,
                    table_name: order.table?.name || null,
                    date: order.date_order || new Date().toISOString(),
                    lines,
                };

                this.bus_service.send("pos_preparation_display.order", orderData);

                console.log("Order sent to Kitchen Display successfully (skipping fiscalization)");
                // Keep is_draft = true to prevent fiscalization during auto-sync
                // Only the Validate button should set is_draft = false
            } catch (error) {
                console.error("Failed to send order to Kitchen Display:", error);
            }
        } else {
            await order.finalize();
            console.log("Order finalized (non-restaurant)");
        }
    },
});
