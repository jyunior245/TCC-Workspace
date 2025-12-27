import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, Button, Card, FAB } from 'react-native-paper';
import axios from 'axios';

export default function HomeScreen() {
  const [lastAnalysis, setLastAnalysis] = useState<any>(null);

  const handleVoiceCommand = async () => {
    // Simulate voice text for MVP (since we can't easily record audio in simulator/mock)
    // In real app, this would use expo-av to record and Whisper to transcribe
    const mockText = "Estou com muita dor de cabeça e febre";
    
    try {
      // Assuming localhost mapping for Android Emulator (10.0.2.2) or using IP
      // For web it works with localhost
      const response = await axios.post('http://localhost:3000/api/voice/process', {
        text: mockText
      });
      setLastAnalysis(response.data);
    } catch (error) {
      console.error(error);
      setLastAnalysis({ error: "Falha ao conectar com o agente" });
    }
  };

  return (
    <View style={styles.container}>
      <Text variant="headlineMedium" style={styles.header}>Olá, João</Text>
      
      <Card style={styles.card}>
        <Card.Title title="Monitoramento" />
        <Card.Content>
          <Text>Medicação: Em dia</Text>
          <Text>Água: 200ml (hoje)</Text>
        </Card.Content>
      </Card>

      {lastAnalysis && (
        <Card style={[styles.card, { backgroundColor: '#f0f0f0' }]}>
          <Card.Title title="Agente IA diz:" />
          <Card.Content>
            <Text>{lastAnalysis.analysis?.feedback || "Erro ao processar"}</Text>
          </Card.Content>
        </Card>
      )}

      <View style={styles.voiceContainer}>
        <FAB
          icon="microphone"
          label="Falar com Agente"
          onPress={handleVoiceCommand}
          style={styles.fab}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#fff',
  },
  header: {
    marginBottom: 20,
  },
  card: {
    marginBottom: 15,
  },
  voiceContainer: {
    flex: 1,
    justifyContent: 'flex-end',
    alignItems: 'center',
    marginBottom: 20,
  },
  fab: {
    backgroundColor: '#6200ee',
  },
});
