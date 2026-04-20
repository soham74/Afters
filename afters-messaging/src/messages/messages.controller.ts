import { Body, Controller, Get, Param, Post, Query } from "@nestjs/common";
import { IsEnum, IsOptional, IsString } from "class-validator";

import { MessagesService } from "./messages.service.js";

class SendDto {
  @IsString()
  user_id!: string;

  @IsString()
  body!: string;

  @IsOptional()
  @IsEnum(["text", "voice_note", "card"])
  kind?: "text" | "voice_note" | "card";

  @IsOptional()
  @IsString()
  session_id?: string | null;

  @IsOptional()
  card_meta?: Record<string, unknown> | null;
}

class ReplyDto {
  @IsString()
  user_id!: string;

  @IsString()
  body!: string;

  @IsOptional()
  @IsString()
  session_id?: string | null;
}

@Controller("messages")
export class MessagesController {
  constructor(private readonly service: MessagesService) {}

  @Post("send")
  async send(@Body() dto: SendDto) {
    return this.service.send(dto);
  }

  @Post("reply")
  async reply(@Body() dto: ReplyDto) {
    return this.service.reply(dto);
  }

  @Get("threads")
  async threads() {
    return this.service.allUsersWithMessages();
  }

  @Get(":userId")
  async thread(@Param("userId") userId: string, @Query("limit") limit?: string) {
    return this.service.thread(userId, limit ? Number(limit) : 200);
  }
}
