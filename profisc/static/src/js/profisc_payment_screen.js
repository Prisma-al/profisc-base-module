/** @odoo-module **/


import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

    patch(PaymentScreen.prototype, {
        setup() {
            super.setup();
            this.pos = usePos();
            this.notification = useService("notification");
            this._profisc_all_payment_methods = [...this.payment_methods_from_config];
            useEffect(
                () => {
                    this._applyProfiscPaymentMethodFilter(this.pos.get_order());
                },
                () => [this.pos.get_order()]
            );
        },
        async onClickDraft() {
            await this.draftOrder()},

        async draftOrder() {
            await this.validateOrder(false, { is_draft: true, sent_fiscal: false });
        },

        async validateOrder(isForceValidate, options = {}) {
            // Custom validation logic.
            const order = this.pos.get_order();

            // Handle is_draft (for backwards compatibility)
            const isDraft = options.is_draft !== undefined ? options.is_draft : false;

            // New flag: sent_fiscal - only true when Validate button is pressed (not Draft)
            const sentFiscal = options.sent_fiscal !== undefined ? options.sent_fiscal : !isDraft;
            const prevIsDraft = order.is_draft;
            const prevSentFiscal = order.sent_fiscal;

            if (!this._custom_validation_method(order)) {
                // Keep previous flags when validation fails so the order stays editable.
                order.is_draft = prevIsDraft;
                order.sent_fiscal = prevSentFiscal;
                return false;
            }

            order.is_draft = isDraft;
            order.sent_fiscal = sentFiscal;
            console.log("Order validation - is_draft:", order.is_draft, "sent_fiscal:", order.sent_fiscal);
            const result = await super.validateOrder(...arguments);

            // Core Odoo validation can still abort after our custom checks.
            // If the order was not finalized, restore the previous flags so later
            // draft/preparation syncs do not reuse a stale sent_fiscal=true value.
            if (!order.finalized) {
                order.is_draft = prevIsDraft;
                order.sent_fiscal = prevSentFiscal;
            }

            return result;
        },

        _custom_validation_method(order) {
            let order_lines = order.get_orderlines() || [];
            let pmt_lines = order.payment_ids || [];
            let cash_count_nr = 0;
            let non_cash_count_nr = 0;
            let has_zero_qty = 0;
            let profisc_fisc_type = parseInt(order.profisc_fisc_type)

            const totalAmount = order.get_total_with_tax();

            console.log("Order total ", totalAmount)
            order_lines.forEach((ol) => {
                if (ol.get_quantity() === 0) {
                    has_zero_qty++;
                }
            });
            pmt_lines.forEach((p) => {
                if (p.payment_method?.is_cash_count) {
                    cash_count_nr++;
                } else {
                    non_cash_count_nr++;
                }
            });
            if (has_zero_qty > 0) {
                this.notification.add(
                    _t('One or more products has quantity = 0.'),
                    { title: _t('Produkte me sasi 0'), type: "danger" }
                );
                return false;
            }

            let selected_partner = order.get_partner?.();
            //maxAmount eshte fusha Vlera Maksimale e vendosur te pos config
            let maxAmount = this.pos.config.max_pos_payment_amount;

            console.log(`Vlera max e vendosur ne pos config ${maxAmount}`);
            console.log(`Vlera e produkteve te blera ${totalAmount}`);
            if (!selected_partner && maxAmount && totalAmount > maxAmount) {
                this.notification.add(
                    _t(`Amount should not exceed ${maxAmount} Leke`),
                    { title: _t('Invalid Amount'), type: "danger" }
                );
                return false;
            }

            if (cash_count_nr > 0 && non_cash_count_nr) {
                this.notification.add(
                    _t('You must select only one payment method type, cash or noncash.'),
                    { title: _t('Multiple payment methods type'), type: "danger" }
                );
                return false;
            }

            // console.log({order, selected_partner})

            if (profisc_fisc_type === 2) {
                if (!selected_partner || selected_partner.profisc_customer_vat_type !== "9923") {
                    this.notification.add(
                        _t('To make an electronic invoice, you must select a valid customer.'),
                        { title: _t('Invalid Customer'), type: "danger" }
                    );
                    return false;
                }
            }

            if (selected_partner && selected_partner.profisc_customer_vat_type === "9923") {
                let is_valid_nuis = this.validateNUIS(selected_partner.vat);
                if (!is_valid_nuis) {
                    this.notification.add(
                        _t('Customer vat_type is NUIS, so a valid NUIS is required in the VAT field.'),
                        { title: _t('Invalid NUIS'), type: "danger" }
                    );
                    return false;
                }
            }
            return true;//duhet true
        },

        _applyProfiscPaymentMethodFilter(order) {
            const profisc_fisc_type = parseInt(order?.profisc_fisc_type);
            const allMethods = this._profisc_all_payment_methods || [];

            /*
                     if the payment method has  is_cash_count equals to true it means that this is a cash payment or noncash method
                     if the payment method has  is_cash_count equals to false it means that this is a noncash payment method
                     in case that the user has chosen 'F.Kontrolli' show all payment methods
                     The difference between 0 and 3 is that the option 0 allows sending to Profisc whereas option 3 only allow showing multiple payment methods but doesn't allow sending to Profisc
             */

            if (profisc_fisc_type === 2) {
                this.payment_methods_from_config = allMethods.filter((p) => {
                    // kontrollo fillimisht me is_cash_count (nëse e ka)
                    if ("is_cash_count" in p) {
                        return !p.is_cash_count;
                    }
                    return p.type !== "cash";
                });
            } else {
                this.payment_methods_from_config = allMethods;
            }
        },

        validateNUIS(str) {
            const regex = /^[A-Za-z]\d{8}[A-Za-z]$/;
            return regex.test(str);
        }

    });
