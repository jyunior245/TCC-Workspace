import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom } from 'rxjs';

@Injectable()
export class GatewayService {
  private flaskUrl: string;

  constructor(
    private httpService: HttpService,
    private configService: ConfigService,
  ) {
    this.flaskUrl = this.configService.get<string>('FLASK_API_URL') || 'http://localhost:5000';
  }

  async processVoice(text: string) {
    const url = `${this.flaskUrl}/process-voice`;
    try {
      const response = await firstValueFrom(
        this.httpService.post(url, { text })
      );
      return response.data;
    } catch (error) {
      throw error;
    }
  }
}

