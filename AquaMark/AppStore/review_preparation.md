# AquaMark — App Review Preparation Guide

## Pre-Submission Checklist

### Technical Requirements
- [ ] App runs on iOS 16.0+
- [ ] Supports iPhone and iPad
- [ ] Supports latest iPhone (6.7" display)
- [ ] Dark mode UI (system preferred)
- [ ] No crashes on launch
- [ ] All navigation paths work
- [ ] Photo library access works correctly
- [ ] Video processing completes without errors
- [ ] StoreKit subscription flow works (test in Sandbox)
- [ ] Restore Purchases button functional
- [ ] Export to Photo Library works
- [ ] All permission dialogs display correct descriptions

### App Store Connect Configuration
- [ ] App name: "AquaMark - Watermark Photo & Video"
- [ ] Bundle ID: com.aquamark.app
- [ ] SKU: AQUAMARK2026
- [ ] Primary language: English
- [ ] Category: Photo & Video
- [ ] Age rating: 4+
- [ ] Price: Free
- [ ] In-App Purchases configured (4 products)
- [ ] Screenshots uploaded (6.7", 6.1", iPad 12.9")
- [ ] App description filled
- [ ] Keywords set
- [ ] Privacy Policy URL live
- [ ] Support URL live
- [ ] Copyright filled
- [ ] App Privacy nutrition labels filled

### Common Rejection Reasons to Avoid
1. **Guideline 2.1 - Performance**: Ensure no crashes
2. **Guideline 3.1.2 - Subscriptions**: 
   - Must clearly describe what Pro unlocks
   - Must have "Restore Purchases" button
   - Terms displayed near purchase button
3. **Guideline 5.1.1 - Privacy**: 
   - Must request photo/camera permissions only when needed
   - Permission descriptions must be clear and specific
4. **Guideline 4.0 - Design**:
   - UI must not look like a web wrapper
   - Must feel native iOS

### Review Notes Template
```
AquaMark is a photo and video watermark editing tool. 
No login is required — all features work without an account.

Free features: Text watermarks on photos, video cropping, standard quality export.
Pro features: Video watermarking, batch processing, 4K export, MD5 modification.

The MD5 modification feature appends random bytes to video files to change the file hash. 
This is commonly used by content creators to avoid duplicate content detection 
on social media platforms. It does not alter the video content or quality.

No test account needed — the app has no login system.
```

### Test Scenarios for Review Team
1. Launch app → Onboarding → Skip to free → Home screen
2. Home → Photo Watermark → Add text → Export
3. Home → Video tools → Crop video → Apply
4. Settings → Subscription → Select plan → Cancel
5. Settings → Restore Purchases

---

## Post-Submission Monitoring

### If Rejected for Guideline 2.1 (Crash/Bug)
- Check crash logs in Xcode Organizer
- Test on all supported device sizes
- Re-test with iOS 16.0 simulator

### If Rejected for Guideline 3.1.2 (Subscription)
- Ensure subscription terms are visible before purchase button
- Verify "Restore Purchases" is accessible
- Confirm all 4 products load correctly from StoreKit

### If Questioned about MD5 Feature
Prepared response:
"The MD5 modification feature is designed for content creators who publish the same promotional content across multiple social media platforms. Many platforms use file hashing to detect duplicate uploads. By modifying the file's hash, creators can distribute their own original content more effectively. The feature only appends benign random bytes to the file — it does not modify the actual video content, and it does not enable any form of piracy or content theft."
