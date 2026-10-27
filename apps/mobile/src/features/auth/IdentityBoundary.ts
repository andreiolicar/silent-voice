import { createElement, Fragment, type PropsWithChildren } from 'react';
/** Reset every navigator and screen-local secret when identity changes, even A -> B. */
export function IdentityBoundary({
  identityKey,
  children,
}: PropsWithChildren<{ identityKey: string }>) {
  return createElement(Fragment, { key: identityKey }, children);
}
