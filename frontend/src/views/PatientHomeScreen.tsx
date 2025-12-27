import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';

export default function PatientHomeScreen() {
  return (
    <View style={styles.container}>
      <Text variant="headlineMedium">Paciente</Text>
      <Text>Bem-vindo. Use o botão de voz para registrar sintomas.</Text>
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

