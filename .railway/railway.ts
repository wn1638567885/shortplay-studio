import { defineRailway, project, service, volume } from "railway/iac";
// This repository manages only its own resources in the environment. Other
// repositories export their own partial name.
// See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "shortplay-studio";
export default defineRailway(() => {
  // 数据卷：SQLite 数据库与上传素材持久化在 /data
  const dataVolume = volume("shortplay-studio-volume", { region: "iad", sizeMB: 500 });

  const shortplayStudio = service("shortplay-studio", {
    build: { buildEnvironment: "V3", builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    healthcheck: "/api/health",
    healthcheckTimeout: 120,
    volumeMounts: { "/data": dataVolume },
    replicas: { "iad": 1 },
  });

  return project("shortplay-studio", {
    variables: { managed: false },
    resources: [shortplayStudio, dataVolume],
  });
});
