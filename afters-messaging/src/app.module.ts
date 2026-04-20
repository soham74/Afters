import { Module } from "@nestjs/common";
import { MessagesModule } from "./messages/messages.module.js";

@Module({
  imports: [MessagesModule],
})
export class AppModule {}
