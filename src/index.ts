import { Container } from "@cloudflare/containers";

export class MerlionContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "10m";

  envVars = {
    GEMINI_API_KEY: this.env.GEMINI_API_KEY,
    LTA_DATAMALL_API_KEY: this.env.LTA_DATAMALL_API_KEY,
  };
}

interface Env {
  MERLION_CONTAINER: DurableObjectNamespace<MerlionContainer>;
  GEMINI_API_KEY: string;
  LTA_DATAMALL_API_KEY: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const container = env.MERLION_CONTAINER.getByName("default");
    return container.fetch(request);
  },
};
