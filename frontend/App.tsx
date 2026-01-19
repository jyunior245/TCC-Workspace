import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { Provider as PaperProvider } from 'react-native-paper';
import LoginScreen from './src/views/LoginScreen';
import RegisterScreen from './src/views/RegisterScreen';
import PatientHomeScreen from './src/views/PatientHomeScreen';
import ACSHomeScreen from './src/views/ACSHomeScreen';
import PatientProfileScreen from './src/views/PatientProfileScreen';
import ACSProfileScreen from './src/views/ACSProfileScreen';

const Stack = createStackNavigator();

export default function App() {
  return (
    <PaperProvider>
      <NavigationContainer>
        <Stack.Navigator initialRouteName="Login">
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
          <Stack.Screen name="PatientProfile" component={PatientProfileScreen} />
          <Stack.Screen name="ACSProfile" component={ACSProfileScreen} />
          <Stack.Screen name="PatientHome" component={PatientHomeScreen} />
          <Stack.Screen name="ACSHome" component={ACSHomeScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </PaperProvider>
  );
}
