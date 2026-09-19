import { useEffect, useState } from 'react';
import { Inbox } from 'lucide-react';

import { LoadingState, EmptyState } from '@/components/ui';
import Tabs from '@/components/ui/Tabs';
import RequestCard from '@/components/RequestCard';
import {
  getIncomingRequests,
  getOutgoingRequests,
  getCompletedRequests,
} from '@/services/requestsService';

const TAB_KEYS = {
  INCOMING: 'incoming',
  OUTGOING: 'outgoing',
  COMPLETED: 'completed',
};

const EMPTY_COPY = {
  [TAB_KEYS.INCOMING]: {
    title: 'No incoming requests',
    description: 'Requests other organizations send you will show up here.',
  },
  [TAB_KEYS.OUTGOING]: {
    title: 'No outgoing requests',
    description: 'Requests you raise with providers or partners will show up here.',
  },
  [TAB_KEYS.COMPLETED]: {
    title: 'No completed requests yet',
    description: 'Delivered and cancelled requests will show up here.',
  },
};

/**
 * Rescue Requests — queue of incoming, outgoing, and completed resource
 * rescue requests.
 *
 * Each tab loads through its own mock service (requestsService), same shape
 * a real endpoint will return later. Search, filters, and a request detail
 * view are later steps; this page only lists and switches between tabs.
 */
export default function RescueRequests() {
  const [activeTab, setActiveTab] = useState(TAB_KEYS.INCOMING);
  const [requestsByTab, setRequestsByTab] = useState({
    [TAB_KEYS.INCOMING]: null,
    [TAB_KEYS.OUTGOING]: null,
    [TAB_KEYS.COMPLETED]: null,
  });

  useEffect(() => {
    let active = true;

    getIncomingRequests().then(
      (data) => active && setRequestsByTab((prev) => ({ ...prev, [TAB_KEYS.INCOMING]: data })),
    );
    getOutgoingRequests().then(
      (data) => active && setRequestsByTab((prev) => ({ ...prev, [TAB_KEYS.OUTGOING]: data })),
    );
    getCompletedRequests().then(
      (data) => active && setRequestsByTab((prev) => ({ ...prev, [TAB_KEYS.COMPLETED]: data })),
    );

    return () => {
      active = false;
    };
  }, []);

  const tabs = [
    { key: TAB_KEYS.INCOMING, label: 'Incoming', count: requestsByTab[TAB_KEYS.INCOMING]?.length },
    { key: TAB_KEYS.OUTGOING, label: 'Outgoing', count: requestsByTab[TAB_KEYS.OUTGOING]?.length },
    {
      key: TAB_KEYS.COMPLETED,
      label: 'Completed',
      count: requestsByTab[TAB_KEYS.COMPLETED]?.length,
    },
  ];

  const activeRequests = requestsByTab[activeTab];
  const emptyCopy = EMPTY_COPY[activeTab];

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">
          Rescue Requests
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          Manage incoming, outgoing, and completed resource rescue requests.
        </p>
      </div>

      <Tabs tabs={tabs} value={activeTab} onChange={setActiveTab} />

      <section>
        {activeRequests === null ? (
          <LoadingState label="Loading requests…" />
        ) : activeRequests.length === 0 ? (
          <div className="panel">
            <EmptyState icon={Inbox} title={emptyCopy.title} description={emptyCopy.description} />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {activeRequests.map((request) => (
              <RequestCard key={request.id} request={request} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
