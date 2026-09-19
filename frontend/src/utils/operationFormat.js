import { STATUS } from '@/utils/theme';

/**
 * Display helpers shared by OperationsTable (desktop) and OperationListCard
 * (mobile / tablet), so both views word the same thing the same way.
 */

/** "80 meals", "340 kg" — quantity with its unit when there is one. */
export function formatQuantity({ quantity, unit }) {
  return unit ? `${quantity} ${unit}` : String(quantity);
}

const ENDED = new Set([STATUS.CANCELLED, STATUS.EXPIRED]);

/**
 * What to show in a Recipient or Rescue Partner cell that has no value.
 * Before an operation ends, an empty cell means "not yet" (with a hint about
 * what is pending); once it has been cancelled or has expired nothing more
 * will happen, so it shows a plain dash.
 */
function emptyLabel(status, pendingText) {
  return ENDED.has(status) ? '—' : pendingText;
}

/** Returns { text, empty } so callers can dim placeholder text. */
export function recipientCell({ recipient, status }) {
  return recipient
    ? { text: recipient, empty: false }
    : { text: emptyLabel(status, 'Awaiting match'), empty: true };
}

/** Returns { text, empty } so callers can dim placeholder text. */
export function partnerCell({ partner, status }) {
  return partner
    ? { text: partner, empty: false }
    : { text: emptyLabel(status, 'Not assigned yet'), empty: true };
}
