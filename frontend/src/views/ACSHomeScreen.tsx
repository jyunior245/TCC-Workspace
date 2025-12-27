import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';

export default function ACSHomeScreen() {
  return (
    <View style={styles.container}>
      <Text variant="headlineMedium">ACS</Text>
      <Text>Monitoramento de alertas e sintomas dos pacientes.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#fff',
  },
});

