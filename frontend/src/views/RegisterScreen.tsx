import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { TextInput, Button, Title, RadioButton } from 'react-native-paper';
import { RegisterViewModel } from '../viewmodels/RegisterViewModel';
import { isValidEmail, isValidPassword } from '../utils/validators';

export default function RegisterScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<'PATIENT' | 'ACS'>('PATIENT');

  const vm = new RegisterViewModel();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async () => {
    setLoading(true);
    setError(null);

    if (!name.trim()) {
      setError('Por favor, insira seu nome.');
      setLoading(false);
      return;
    }

    if (!isValidEmail(email)) {
      setError('Email inválido. Verifique o formato (ex: nome@dominio.com).');
      setLoading(false);
      return;
    }

    if (!isValidPassword(password)) {
      setError('A senha deve ter pelo menos 6 caracteres.');
      setLoading(false);
      return;
    }

    try {
      await vm.register(email, password, name, role);
      navigation.replace('Login');
    } catch (e: any) {
      console.error('Register error:', e);
      if (e.response && e.response.status === 409) {
        setError('Este email já está sendo usado. Tente outro.');
      } else {
        setError('Falha ao cadastrar. Verifique os dados e tente novamente.');
      }
    } finally {
      setLoading(false);
    }
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

      <Button mode="contained" onPress={handleRegister} disabled={loading} style={styles.button}>
        Cadastrar
      </Button>
      {error && <Title style={{ color: 'red', marginTop: 10 }}>{error}</Title>}
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
