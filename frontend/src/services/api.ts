import axios from 'axios';
import { Platform } from 'react-native';

const baseURL = Platform.OS === 'android' ? 'http://10.0.0.4:3000' : 'http://localhost:3000';

export const api = axios.create({
  baseURL,
  timeout: 10000, // 10 seconds timeout
});

