# Navigation / Roundabout / Alert fixes

- Navigation guidance progress now follows the 60fps predicted vehicle position; raw GPS is used separately for off-route validation.
- Navigation and reroute origins use the same smoothed/map-matched position shown by the marker, reducing start-position mismatch.
- Roundabout maneuvers now carry a total exit count from the offline graph and the guidance icon renders all detected exits while highlighting the selected/main exit.
- Roundabout exit counting avoids counting the same connected road multiple times across several roundabout nodes.
- During navigation, only one road alert is shown at a time, only within 100 m ahead of the vehicle.
- Passed alerts disappear immediately; the previous stacked two-alert behavior and 600 m display window are removed.
- Online safety-layer fallback also checks heading so a passed/behind alert is not shown as an upcoming warning.
