# Studio architecture

The website accepts reviewed exports as inputs. The editable art workspace owns the Blender scenes, modeling history, reference images, texture sources and export recipes. A clean website checkout builds with Node.js and the dependencies in the lockfile.

## Where a change belongs

| Change                                                | Owner                                                                                                                                                            | Verification                                                                     |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Change which physical fixture a phone switch controls | The light definitions and actions in `src/app/home-lights.ts`. The scene and the phone use the same action.                                                      | Compare the phone, the physical fixture and the light after a daylight reload.   |
| Change how an inspection ends                         | The scene interaction types in `src/scene/interaction.ts` and the camera controller in `StudioView.tsx`. DOM controls call the same exit action as the keyboard. | Return from the bookshelf and cabinet with normal and reduced motion.            |
| Change device defaults or restore preferences         | `src/app/graphics-device.ts` selects the initial render quality. `src/app/environment-preferences.ts` restores the environment using the existing storage key.   | Check the desktop and compact entry points, saved settings and local daylight.   |
| Change an object's sculpt or materials                | The art workspace. Import the approved browser export into `public/media/models/` with its measured scale and the node or material names used by the scene.      | Verify the export in the installed object and in each supported inspection mode. |
| Change how model files reach the browser              | The web build in `scripts/build/studio-parts.ts` and the matching readers in `src/scene/`.                                                                       | Compare each unpacked mesh with its input and exercise the production build.     |

## Build and delivery

1. Start with the checked-in model exports, lighting data, textures and audio. Some art changes also produce scene data such as fitted dimensions or light samples. Bring those across with the corresponding model.
2. The build creates `room-parts.bpk` for synchronously constructed room objects and `workshop-tools.bpk` for the deferred tool board. A GLB stays independently addressable where the application can load it on its own. Standalone assemblies such as the printer retain their dedicated packages.
3. The model loader chooses the representation needed by the scene. The build can strip concealed surfaces from an installed assembly and gzip the result. The export kept for testing and the installed model served to the browser can therefore have different sizes.
4. Publish `dist/`. Asset URLs describe their use. Deploy the matching code and assets together. If a separate CDN serves stable URLs, use revalidation or invalidate changed files when publishing.

## Maintenance checks

The [Studio performance spec](specs/2026-11-22-studio-performance.md) records the measured baseline and next experiments. The [performance standards](performance-standards.md) define hardware and visual acceptance.

Run `npm run build` and `npm run test:ci` from the website checkout. For navigation and lighting changes, also run `npm test -- tests/bookshelf-view.spec.ts tests/phone-home.spec.ts`. Set `STUDIO_TEST_PORT` to an unused port to run against a fresh local server. Production smoke checks should request media from the built static site because the development server also supports authoring previews.
