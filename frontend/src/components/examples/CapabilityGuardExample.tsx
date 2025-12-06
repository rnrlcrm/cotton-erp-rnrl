/**
 * Example Component Demonstrating Capability Guards
 * 
 * Shows how to use capability-based permissions in components
 */

import { 
  RequireCapability, 
  RequireAnyCapability,
  useHasCapability,
  useIsAdmin,
} from '@/hooks/useCapabilities';
import { CapabilityCode } from '@/types/capability';
import { 
  ShieldCheckIcon,
  KeyIcon,
  LockClosedIcon,
} from '@heroicons/react/24/outline';

export function CapabilityGuardExample() {
  const canCreateAvailability = useHasCapability(CapabilityCode.AVAILABILITY_CREATE);
  const canApproveMatch = useHasCapability(CapabilityCode.MATCHING_APPROVE_MATCH);
  const isAdmin = useIsAdmin();

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      <div className="bg-white border-2 border-space-200 rounded-2xl p-6">
        <h2 className="text-2xl font-heading font-bold text-space-900 mb-4">
          Capability Guard Examples
        </h2>
        <p className="text-saturn-600 mb-6">
          These components render based on user's capabilities
        </p>

        {/* Example 1: Simple capability check */}
        <div className="space-y-4">
          <div className="border-2 border-space-200 rounded-xl p-4">
            <h3 className="font-bold text-space-900 mb-2">1. Hook-based Check</h3>
            {canCreateAvailability ? (
              <div className="flex items-center gap-2 text-emerald-600">
                <ShieldCheckIcon className="w-5 h-5" />
                <span>You can create availability (AVAILABILITY_CREATE)</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-600">
                <LockClosedIcon className="w-5 h-5" />
                <span>You cannot create availability (missing AVAILABILITY_CREATE)</span>
              </div>
            )}
          </div>

          {/* Example 2: Component guard */}
          <div className="border-2 border-space-200 rounded-xl p-4">
            <h3 className="font-bold text-space-900 mb-2">2. Component Guard</h3>
            <RequireCapability
              capability={CapabilityCode.AVAILABILITY_CREATE}
              fallback={
                <div className="flex items-center gap-2 text-red-600">
                  <LockClosedIcon className="w-5 h-5" />
                  <span>This button is hidden (requires AVAILABILITY_CREATE)</span>
                </div>
              }
            >
              <button className="px-4 py-2 bg-emerald-500 text-white rounded-lg font-bold">
                + Create Availability
              </button>
            </RequireCapability>
          </div>

          {/* Example 3: Multiple capabilities (ANY) */}
          <div className="border-2 border-space-200 rounded-xl p-4">
            <h3 className="font-bold text-space-900 mb-2">3. Any Capability</h3>
            <RequireAnyCapability
              capabilities={[
                CapabilityCode.AVAILABILITY_APPROVE,
                CapabilityCode.REQUIREMENT_APPROVE,
                CapabilityCode.MATCHING_APPROVE_MATCH,
              ]}
              fallback={
                <div className="flex items-center gap-2 text-red-600">
                  <LockClosedIcon className="w-5 h-5" />
                  <span>No approval capabilities</span>
                </div>
              }
            >
              <div className="flex items-center gap-2 text-sun-600">
                <KeyIcon className="w-5 h-5" />
                <span>You have at least one approval capability</span>
              </div>
            </RequireAnyCapability>
          </div>

          {/* Example 4: Admin check */}
          <div className="border-2 border-space-200 rounded-xl p-4">
            <h3 className="font-bold text-space-900 mb-2">4. Admin Check</h3>
            {isAdmin ? (
              <div className="flex items-center gap-2 text-mars-600">
                <ShieldCheckIcon className="w-5 h-5" />
                <span className="font-bold">ADMIN ACCESS GRANTED</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-saturn-600">
                <KeyIcon className="w-5 h-5" />
                <span>Standard user access</span>
              </div>
            )}
          </div>

          {/* Example 5: Conditional rendering in JSX */}
          <div className="border-2 border-space-200 rounded-xl p-4">
            <h3 className="font-bold text-space-900 mb-2">5. Multiple Buttons</h3>
            <div className="flex gap-3">
              <RequireCapability capability={CapabilityCode.AVAILABILITY_CREATE}>
                <button className="px-4 py-2 bg-blue-500 text-white rounded-lg">
                  Create Availability
                </button>
              </RequireCapability>
              
              <RequireCapability capability={CapabilityCode.REQUIREMENT_CREATE}>
                <button className="px-4 py-2 bg-purple-500 text-white rounded-lg">
                  Create Requirement
                </button>
              </RequireCapability>
              
              <RequireCapability capability={CapabilityCode.MATCHING_EXECUTE}>
                <button className="px-4 py-2 bg-teal-500 text-white rounded-lg">
                  Execute Matching
                </button>
              </RequireCapability>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
