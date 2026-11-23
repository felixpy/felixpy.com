import type { Object3D } from 'three';

export function productDetail() {
  const authoring =
    import.meta.env.DEV && new URLSearchParams(location.search).get('review') === 'authoring';
  const inspectionParts: Object3D[] = [];
  let inspecting = false;
  return {
    enclosed(part: Object3D) {
      part.visible = authoring;
    },
    close(part: Object3D) {
      inspectionParts.push(part);
      part.visible = authoring || inspecting;
    },
    select(active: boolean) {
      if (inspecting === active) return;
      inspecting = active;
      for (const part of inspectionParts) part.visible = authoring || active;
    },
  };
}

export type ProductDetail = ReturnType<typeof productDetail>;
