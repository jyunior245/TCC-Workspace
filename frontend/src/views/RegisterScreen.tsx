import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { TextInput, Button, Title, RadioButton } from 'react-native-paper';
import { RegisterViewModel } from '../viewmodels/RegisterViewModel';

export default function RegisterScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<'PATIENT' | 'ACS'>('PATIENT');

  const vm = new RegisterViewModel();

  const handleRegister = async () => {
    await vm.register(email, password, name, role);
    navigation.replace('Login');
  };

  return (
    <View style={styles.container}>
      <Title style={styles.title}>Criar Conta</Title>
      <TextInput label="Nome" value={name} onChangeText={setName} style={styles.input} />
      <TextInput label="Email" value={email} onChangeText={setEmail} style={styles.input} />
      <TextInput label="Senha" value={password} onChangeText={setPassword} secureTextEntry style={styles.input} />

      <RadioButton.Group onValueChange={value => setRole(value as 'PATIENT' | 'ACS')} value={role}>
        <RadioButton.Item label="Paciente" value="PATIENT" />
        <RadioButton.Item label="Agente Comunitário de Saúde" value="ACS" />
      </RadioButton.Group>

      <Button mode="contained" onPress={handleRegister} style={styles.button}>
        Cadastrar
      </Button>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    textAlign: 'center',
    marginBottom: 20,
  },
  input: {
    marginBottom: 10,
  },
  button: {
    marginTop: 10,
  },
});

