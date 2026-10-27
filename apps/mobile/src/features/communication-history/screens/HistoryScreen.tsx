import { useLocalSearchParams } from 'expo-router';
import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';

import { ScreenHeading } from '@/components/layout';
import { MainAppScreen } from '@/features/system-overview/components/MainAppScreen';
import { SystemAppHeader } from '@/features/system-overview/components/SystemAppHeader';
import { spacing } from '@/theme';

import { HistoryEmptyState } from '../components/HistoryEmptyState';
import { HistoryGroupCard } from '../components/HistoryGroupCard';
import { communicationHistoryMock } from '../data/communication-history.mock';
import { groupCommunicationHistory } from '../data/group-communication-history';

export default function HistoryScreen() {
  const params = useLocalSearchParams<{ empty?: string | string[] }>();
  const emptyParam = Array.isArray(params.empty)
    ? params.empty[0]
    : params.empty;
  const showEmptyState = emptyParam === 'true';
  const groups = useMemo(
    () =>
      groupCommunicationHistory(showEmptyState ? [] : communicationHistoryMock),
    [showEmptyState],
  );

  return (
    <MainAppScreen activeItem="history">
      <SystemAppHeader />

      <View style={styles.heading}>
        <ScreenHeading
          subtitle="Suas comunicações recentes."
          title="Histórico"
        />
      </View>

      <View style={styles.section}>
        {groups.length === 0 ? (
          <HistoryEmptyState />
        ) : (
          groups.map((group) => (
            <HistoryGroupCard group={group} key={group.dateKey} />
          ))
        )}
      </View>
    </MainAppScreen>
  );
}

const styles = StyleSheet.create({
  heading: { marginTop: spacing.section },
  section: { gap: spacing.lg, marginTop: spacing.section },
});
