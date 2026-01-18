import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { TextInput, Button, Title } from 'react-native-paper';
import { LoginViewModel } from '../viewmodels/LoginViewModel';
import { isValidEmail } from '../utils/validators';

export default function LoginScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const vm = new LoginViewModel();

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await vm.loginAndRoute(email, password);
      navigation.replace(result.route);
    } catch (e: any) {
      console.error('Login error:', e);
      setError('Falha ao entrar. Verifique email/senha.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Title style={styles.title}>TCC Saúde Assistiva</Title>
      <TextInput
        label="Email"
        value={email}
        onChangeText={setEmail}
        style={styles.input}
      />
      <TextInput
        label="Senha"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        style={styles.input}
      />
      <Button mode="contained" onPress={handleLogin} disabled={loading} style={styles.button}>
        Entrar
      </Button>
      <Button onPress={() => navigation.navigate('Register')} style={styles.link}>
        Criar conta
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
  link: {
    marginTop: 10,
  },
});
