declare module "react" {
  export const StrictMode: any;
}

declare module "react-dom/client" {
  export function createRoot(element: Element): { render(value: any): void };
}

declare module "react/jsx-runtime" {
  export const Fragment: any;
  export function jsx(type: any, props: any): any;
  export function jsxs(type: any, props: any): any;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elementName: string]: any;
  }
}
