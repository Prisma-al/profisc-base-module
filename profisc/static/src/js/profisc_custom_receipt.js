/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    setPartner(partner) {
        super.setPartner(partner);

        if (this.to_invoice) {
            this.to_invoice = false;
        }
    },

    async wait_for_push_order() {
        const pushed = await super.wait_for_push_order(...arguments);

        if (pushed) {
            await this.pos.getOrderData(this);
            this.sent_fiscal = false;
            if (this.raw) {
                this.raw.sent_fiscal = false;
            }
        }

        return Boolean(pushed);
    },
});
