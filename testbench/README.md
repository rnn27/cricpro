# cricpro test bench (phone + PC)

Use your phone to test the speed engine on real clips. The phone records with its normal camera
app (240 fps slow-motion), then uses this page, served from your PC over Wi-Fi, to upload the clip,
tap the stumps, mark the release frame and read the speed. All processing happens on your PC.

This is an interim tool for testing. The proper app (in-app 240 fps recorder with exact frame
timestamps) comes next; see docs/journey/05.

## Run (Windows PowerShell)
    cd testbench
    py -m pip install -r requirements.txt
    py server.py
It prints two addresses. Open the `On your phone` one in the phone's browser (phone and PC on the
same Wi-Fi). If Windows asks about the firewall, allow Python on **private** networks.
If the phone cannot connect: check the Wi-Fi is the same, and that the PC's network is set to Private.
No password: only run on a Wi-Fi you trust.

## Flow
1. Upload the clip and confirm the capture fps (the page shows how many seconds of real time the
   clip covers, as a sanity check).
2. Tap the stump base and top at each end. Fine-tune in the zoom square.
3. Scrub to the release frame and mark it.
4. Optionally enter the reference speed, camera distance and ball offset, then Calculate.
5. History -> Download results.csv for the validation log.

## Notes
- Timing here is *assumed* from the fps you enter (no sensor timestamps), so every result carries the
  "timing assumed" warning and a wider uncertainty.
- iPhone: the browser's picker may re-compress or flatten slow-motion videos. If the page reports an
  odd frame count or length, move the original file to the PC (AirDrop/cable) and use the page there.
- Data is stored in `testbench/data/` (ignored by git).
- Phone-side touch behaviour could not be tested where this was written (no phone). Report anything odd.
