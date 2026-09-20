import { History } from 'lucide-react';

import { Card, EmptyState } from '@/components/ui';
import ActivityTimeline from '@/components/ActivityTimeline';

/**
 * OperationEventsCard — the event feed of the selected operation, in the
 * Operations details view.
 *
 * Where OperationStageTracker lists the whole lifecycle (including the stages
 * still to come), this lists only what has already happened, newest first. A
 * change part-way through an operation is recorded here: when the RS-1024
 * demo recipient becomes unavailable, the feed gains the cause and, once the
 * updated allocation is confirmed, the explanation of what changed.
 *
 * Frontend only: events come from the same mock detail payload as the rest of
 * the page (see services/rescueOperationsService.js) and every time shown is
 * a hardcoded, illustrative label — never a live clock.
 */
export default function OperationEventsCard({ events = [] }) {
  return (
    <Card>
      <Card.Header
        icon={History}
        title="Operation Events"
        subtitle="What has happened on this operation so far, newest first."
      />
      <Card.Body>
        {events.length === 0 ? (
          <EmptyState
            icon={History}
            title="No events yet"
            description="Events appear here as the operation progresses."
          />
        ) : (
          <>
            <ActivityTimeline items={events} wrapText />
            <p className="mt-4 border-t border-line pt-3 text-[11px] text-faint">
              Demo event feed — timestamps are hardcoded, illustrative values, and no notification
              was sent to any organization.
            </p>
          </>
        )}
      </Card.Body>
    </Card>
  );
}
