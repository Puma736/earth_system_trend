import {
  createTheme,
  type CSSVariablesResolver,
  type MantineColorsTuple,
} from "@mantine/core";

const signal: MantineColorsTuple = [
  "#f6f8d4",
  "#eceeab",
  "#e0e46e",
  "#d5db45",
  "#cdd634",
  "#CBD931",
  "#b3c028",
  "#8e9920",
  "#6a7318",
  "#464d10",
];

const indigo: MantineColorsTuple = [
  "#e7e9f6",
  "#c5c9e8",
  "#9aa2d4",
  "#707bbf",
  "#5560ab",
  "#3D4B97",
  "#354388",
  "#2c3873",
  "#242d5f",
  "#1b234b",
];

const dark: MantineColorsTuple = [
  "#A0A0A5",
  "#A0A0A5",
  "#A0A0A5",
  "#6d6d72",
  "#39383A",
  "#39383A",
  "#151722",
  "#151722",
  "#151722",
  "#151722",
];

export const theme = createTheme({
  primaryColor: "signal",
  primaryShade: 5,
  autoContrast: true,
  luminanceThreshold: 0.45,
  defaultRadius: "sm",
  cursorType: "pointer",
  black: "#151722",
  white: "#A0A0A5",
  fontFamily: '"Familjen Grotesk", "Segoe UI", sans-serif',
  fontFamilyMonospace: '"IBM Plex Mono", Consolas, monospace',
  headings: {
    fontFamily: '"Familjen Grotesk", "Segoe UI", sans-serif',
    fontWeight: "560",
  },
  colors: {
    signal,
    indigo,
    dark,
  },
  components: {
    Paper: {
      defaultProps: {
        bg: "#39383A",
        radius: "md",
        shadow: "none",
      },
    },
  },
});

export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {
    "--mantine-color-body": "#151722",
    "--mantine-color-text": "#A0A0A5",
  },
  light: {
    "--mantine-color-body": "#151722",
    "--mantine-color-text": "#A0A0A5",
  },
  dark: {
    "--mantine-color-body": "#151722",
    "--mantine-color-text": "#A0A0A5",
    "--mantine-color-dimmed": "#A0A0A5",
  },
});
