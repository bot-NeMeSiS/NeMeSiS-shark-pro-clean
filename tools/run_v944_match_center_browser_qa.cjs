#!/usr/bin/env node
"use strict";

// Focused read-only Browser QA for the V944 Match Center foundation.

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const PROFILES = {
  desktop_1366x768: { width: 1366, height: 768, isMobile: false },
  tablet_834x1194: { width: 834, height: 1194, isMobile: false },
  mobile_390x844: { width: 390, height: 844, isMobile: true },
};
const SCENARIOS = {
  ready: "/match/v944-ready",
  partial: "/match/v944-partial",
};
const COMPONENTS = [
  "MatchHeader",
  "ScoreWidget",
  "MatchStory",
  "Timeline",
  "StatsPanel",
  "SharkPanel",
  "TelegramPanel",
  "BankrollPanel",
  "CompetitionPanel",
  "QuickActions",
];
const STATES = [
  "loading",
  "ready",
  "partial",
  "finished",
  "error",
  "offline",
  "unknown",
];
const BLOCKED_PROVIDER_HOSTS = [
  "api-sports",
  "api-football",
  "thesportsdb",
  "the-odds-api",
  "api.telegram",
  "api.openai",
  "stripe.com",
];

function argValue(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function madridNow() {
  const formatter = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Europe/Madrid",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  return formatter.format(new Date()).replace(" ", "T") + "[Europe/Madrid]";
}

async function inspectPage(page) {
  return page.evaluate(
    ({ components, states }) => {
      const root = document.querySelector("[data-v944-match-center-foundation]");
      const visibleText = (root ? root.innerText : document.body.innerText)
        .replace(/\s+/g, " ")
        .trim();
      const componentNodes = Array.from(
        document.querySelectorAll("[data-match-component]")
      );
      const names = componentNodes.map((node) =>
        node.getAttribute("data-match-component")
      );
      const stateValues = componentNodes.map((node) =>
        node.getAttribute("data-component-state")
      );
      const actions = Array.from(
        (root || document).querySelectorAll("a, button, input, select")
      );
      const smallTargets = actions
        .filter((node) => {
          const rect = node.getBoundingClientRect();
          return (
            rect.width > 0 &&
            rect.height > 0 &&
            (rect.width < 32 || rect.height < 32)
          );
        })
        .map((node) => {
          const rect = node.getBoundingClientRect();
          return {
            text: (
              node.innerText ||
              node.getAttribute("aria-label") ||
              ""
            ).trim(),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          };
        });
      const clippedText = Array.from(
        (root || document).querySelectorAll("strong, p, span, small, a")
      )
        .filter((node) => {
          const style = getComputedStyle(node);
          return (
            style.overflow === "hidden" &&
            (node.scrollWidth > node.clientWidth + 1 ||
              node.scrollHeight > node.clientHeight + 1) &&
            style.textOverflow !== "ellipsis"
          );
        })
        .map((node) => (node.textContent || "").trim().slice(0, 100));
      return {
        root_count: document.querySelectorAll(
          "[data-v944-match-center-foundation]"
        ).length,
        contract: root?.getAttribute("data-match-contract") || "",
        shell_state: root?.getAttribute("data-match-state") || "",
        component_count: componentNodes.length,
        component_names: names,
        component_names_unique: new Set(names).size,
        missing_components: components.filter((name) => !names.includes(name)),
        invalid_states: stateValues.filter((state) => !states.includes(state)),
        region_count: document.querySelectorAll("[data-match-region]").length,
        horizontal_overflow:
          document.documentElement.scrollWidth > window.innerWidth + 1,
        document_width: document.documentElement.scrollWidth,
        viewport_width: window.innerWidth,
        old_hero_count: document.querySelectorAll(".v933-match-hero").length,
        old_tabs_count: document.querySelectorAll(".v933-detail-tabs").length,
        client_sidebar_count:
          document.querySelectorAll(".ns-client-sidebar").length,
        mobile_bottom_nav_count: document.querySelectorAll(
          ".bottom-nav, .v933-mobile-bottom-nav"
        ).length,
        admin_nav_count: document.querySelectorAll(
          ".ns-admin-sidebar, [data-admin-sidebar]"
        ).length,
        unsafe_literal_visible: /\b(?:None|null|undefined)\b/.test(visibleText),
        technical_state_visible:
          /\b(?:READY|PARTIAL|UNKNOWN|OFFLINE|LOADING)\b/.test(visibleText),
        visible_text_length: visibleText.length,
        small_targets: smallTargets,
        clipped_text: clippedText,
        cls: Number(window.__v944CLS || 0),
      };
    },
    { components: COMPONENTS, states: STATES }
  );
}

async function main() {
  const baseUrl = argValue("--base-url", "http://127.0.0.1:5095");
  const output = path.resolve(
    argValue(
      "--output",
      path.join(ROOT, "browser_qa", "V944_MATCH_CENTER_FOUNDATION")
    )
  );
  fs.mkdirSync(output, { recursive: true });
  const baseHost = new URL(baseUrl).host.toLowerCase();
  const results = [];
  const browser = await chromium.launch({ headless: true });

  try {
    for (const [profileName, profile] of Object.entries(PROFILES)) {
      const context = await browser.newContext({
        viewport: { width: profile.width, height: profile.height },
        deviceScaleFactor: 1,
        isMobile: profile.isMobile,
        hasTouch: profile.isMobile,
        locale: "es-ES",
        timezoneId: "Europe/Madrid",
      });
      await context.addInitScript(() => {
        window.__v944CLS = 0;
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) window.__v944CLS += entry.value;
          }
        }).observe({ type: "layout-shift", buffered: true });
      });

      for (const [scenario, route] of Object.entries(SCENARIOS)) {
        const page = await context.newPage();
        const consoleErrors = [];
        const pageErrors = [];
        const serverErrors = [];
        const externalRequests = [];
        const providerRequests = [];
        page.on("console", (message) => {
          if (message.type() === "error") consoleErrors.push(message.text());
        });
        page.on("pageerror", (error) => pageErrors.push(String(error)));
        page.on("response", (response) => {
          if (response.status() >= 500) {
            serverErrors.push({ status: response.status(), url: response.url() });
          }
        });
        page.on("request", (request) => {
          const host = new URL(request.url()).host.toLowerCase();
          if (host && host !== baseHost) externalRequests.push(request.url());
          if (BLOCKED_PROVIDER_HOSTS.some((token) => host.includes(token))) {
            providerRequests.push(request.url());
          }
        });

        const url = new URL(route, baseUrl).toString();
        const response = await page.goto(url, {
          waitUntil: "networkidle",
          timeout: 30000,
        });
        await page.waitForTimeout(500);
        const metrics = await inspectPage(page);
        const screenshot = path.join(
          output,
          `${profileName}__${scenario}.png`
        );
        await page.screenshot({ path: screenshot, fullPage: true });
        const failures = [];

        if (!response || response.status() !== 200) {
          failures.push(`http_status=${response ? response.status() : "none"}`);
        }
        if (metrics.root_count !== 1) {
          failures.push("match_center_root_not_unique");
        }
        if (metrics.contract !== "MATCH-CENTER-LIFECYCLE-STORY-V1") {
          failures.push("match_center_contract_missing");
        }
        if (metrics.component_count !== COMPONENTS.length) {
          failures.push("component_count_mismatch");
        }
        if (metrics.component_names_unique !== COMPONENTS.length) {
          failures.push("component_contract_duplicated");
        }
        if (metrics.missing_components.length) {
          failures.push("component_contract_missing");
        }
        if (metrics.invalid_states.length) {
          failures.push("invalid_component_state");
        }
        if (metrics.horizontal_overflow) failures.push("horizontal_overflow");
        if (metrics.old_hero_count || metrics.old_tabs_count) {
          failures.push("legacy_match_shell_duplicated");
        }
        if (metrics.client_sidebar_count > 1) {
          failures.push("client_sidebar_duplicated");
        }
        if (metrics.mobile_bottom_nav_count > 1) {
          failures.push("mobile_navigation_duplicated");
        }
        if (metrics.admin_nav_count) {
          failures.push("admin_navigation_mixed_into_client");
        }
        if (metrics.unsafe_literal_visible) {
          failures.push("unsafe_literal_visible");
        }
        if (metrics.technical_state_visible) {
          failures.push("technical_state_visible");
        }
        if (metrics.clipped_text.length) failures.push("clipped_text");
        if (metrics.cls > 0.05) failures.push("layout_shift_over_budget");
        if (profile.isMobile && metrics.small_targets.length) {
          failures.push("small_mobile_target");
        }
        if (consoleErrors.length) failures.push("console_errors");
        if (pageErrors.length) failures.push("page_errors");
        if (serverErrors.length) failures.push("server_5xx");
        if (providerRequests.length) {
          failures.push("provider_call_during_render");
        }

        results.push({
          profile: profileName,
          scenario,
          route,
          url,
          http_status: response ? response.status() : null,
          screenshot: path
            .relative(ROOT, screenshot)
            .split(path.sep)
            .join("/"),
          metrics,
          console_errors: consoleErrors,
          page_errors: pageErrors,
          server_errors: serverErrors,
          external_requests: [...new Set(externalRequests)].sort(),
          provider_requests: [...new Set(providerRequests)].sort(),
          failures,
          status: failures.length ? "FAIL" : "PASS",
        });
        await page.close();
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }

  const failures = results
    .filter((item) => item.failures.length)
    .map((item) => ({
      profile: item.profile,
      scenario: item.scenario,
      failures: item.failures,
    }));
  const payload = {
    sprint: "V944_MATCH_CENTER_FOUNDATION_PHASE_1_FINAL",
    runtime_modified: false,
    generated_at_madrid: madridNow(),
    base_url: baseUrl,
    read_only: true,
    production_modified: false,
    screenshots_captured: results.length,
    profiles: Object.keys(PROFILES),
    scenarios: Object.keys(SCENARIOS),
    status: failures.length ? "FAIL" : "PASS",
    failures,
    results,
  };
  fs.writeFileSync(
    path.join(output, "browser_qa_result.json"),
    JSON.stringify(payload, null, 2) + "\n",
    "utf8"
  );
  process.stdout.write(JSON.stringify(payload, null, 2) + "\n");
  return failures.length ? 1 : 0;
}

main()
  .then((code) => {
    process.exitCode = code;
  })
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
