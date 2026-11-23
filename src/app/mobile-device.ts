type DeviceNavigator = Pick<Navigator, 'userAgent' | 'maxTouchPoints'> & {
  userAgentData?: { mobile?: boolean; platform?: string };
};

export function isMobileDevice({ userAgent, maxTouchPoints, userAgentData }: DeviceNavigator) {
  return (
    userAgentData?.mobile === true ||
    userAgentData?.platform === 'Android' ||
    /Android|iPhone|iPad|iPod|Mobile|Silk/i.test(userAgent) ||
    (/Macintosh/i.test(userAgent) && maxTouchPoints > 1)
  );
}
