import {
  ConflictException,
  Injectable,
  Logger,
  OnModuleDestroy,
  OnModuleInit,
} from "@nestjs/common";
import { Collection, MongoClient, ObjectId } from "mongodb";
import Redis from "ioredis";
import axios from "axios";

export interface MessageRecord {
  _id: string;
  user_id: string;
  direction: "outbound" | "inbound";
  body: string;
  kind: "text" | "voice_note" | "card";
  card_meta?: Record<string, unknown> | null;
  session_id?: string | null;
  created_at: Date;
}

@Injectable()
export class MessagesService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(MessagesService.name);
  private mongo!: MongoClient;
  private redis!: Redis;
  private messages!: Collection<MessageRecord>;
  private orchestratorBase!: string;

  async onModuleInit() {
    const uri = process.env.MONGODB_URI ?? "mongodb://localhost:27017/afters";
    this.mongo = new MongoClient(uri);
    await this.mongo.connect();
    // Hardcoded for the deploy. URI-segment parsing breaks on Railway-style
    // mongodb URIs that have no db path; MONGO_DB_NAME_OVERRIDE mirrors the
    // env var the orchestrator already reads, so both services share one knob.
    const dbName = process.env.MONGO_DB_NAME_OVERRIDE || "afters";
    this.messages = this.mongo.db(dbName).collection<MessageRecord>("messages");
    await this.messages.createIndex({ user_id: 1, created_at: -1 });

    this.redis = new Redis(process.env.REDIS_URL ?? "redis://localhost:6379");
    this.orchestratorBase = process.env.ORCHESTRATOR_BASE_URL ?? "http://localhost:8000";
    this.logger.log("mongo + redis connected");
  }

  async onModuleDestroy() {
    await this.mongo?.close();
    this.redis?.disconnect();
  }

  async send(payload: {
    user_id: string;
    body: string;
    kind?: "text" | "voice_note" | "card";
    session_id?: string | null;
    card_meta?: Record<string, unknown> | null;
  }): Promise<MessageRecord> {
    const message: MessageRecord = {
      _id: new ObjectId().toHexString(),
      user_id: payload.user_id,
      direction: "outbound",
      body: payload.body,
      kind: payload.kind ?? "text",
      card_meta: payload.card_meta ?? null,
      session_id: payload.session_id ?? null,
      created_at: new Date(),
    };
    await this.messages.insertOne(message);
    await this.redis.publish(
      `afters:chat:${payload.user_id}`,
      JSON.stringify({ type: "outbound", message }),
    );
    return message;
  }

  async reply(payload: {
    user_id: string;
    body: string;
    session_id?: string | null;
  }): Promise<MessageRecord> {
    const message: MessageRecord = {
      _id: new ObjectId().toHexString(),
      user_id: payload.user_id,
      direction: "inbound",
      body: payload.body,
      kind: "text",
      card_meta: null,
      session_id: payload.session_id ?? null,
      created_at: new Date(),
    };
    await this.messages.insertOne(message);
    await this.redis.publish(
      `afters:chat:${payload.user_id}`,
      JSON.stringify({ type: "inbound", message }),
    );

    // Notify the orchestrator so it can run Debrief Intake. If the orchestrator
    // rejects with 409 (terminal session), surface it to the caller; the message
    // is already in the thread so the reviewer can see what they typed, but the
    // state machine will not advance.
    try {
      await axios.post(`${this.orchestratorBase}/api/webhook/user_reply`, {
        user_id: payload.user_id,
        body: payload.body,
        session_id: payload.session_id ?? null,
      });
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 409) {
        throw new ConflictException(
          detail ?? "session already resolved. no further replies processed.",
        );
      }
      this.logger.warn(
        `webhook to orchestrator failed: ${err?.message ?? err}`,
      );
    }
    return message;
  }

  async thread(userId: string, limit = 200): Promise<MessageRecord[]> {
    return this.messages
      .find({ user_id: userId })
      .sort({ created_at: 1 })
      .limit(limit)
      .toArray();
  }

  async allUsersWithMessages(): Promise<Array<{ user_id: string; last_at: Date }>> {
    const out = await this.messages
      .aggregate<{ _id: string; last_at: Date }>([
        { $sort: { created_at: -1 } },
        { $group: { _id: "$user_id", last_at: { $first: "$created_at" } } },
        { $sort: { last_at: -1 } },
      ])
      .toArray();
    return out.map((row) => ({ user_id: row._id, last_at: row.last_at }));
  }
}
