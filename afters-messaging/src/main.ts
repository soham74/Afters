import "reflect-metadata";
import { NestFactory } from "@nestjs/core";
import { ValidationPipe } from "@nestjs/common";
import * as dotenv from "dotenv";
import * as path from "node:path";

import { AppModule } from "./app.module.js";

dotenv.config({ path: path.resolve(__dirname, "..", "..", ".env") });

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    cors: { origin: true },
  });
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  const port = Number(process.env.MESSAGING_PORT || 3001);
  await app.listen(port);
  console.log(`[afters-messaging] up on :${port}`);
}

bootstrap();
