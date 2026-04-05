# AquaMark — Professional Watermark Studio

<p align="center">
  <strong>Protect your creative content with beautiful watermarks.</strong><br>
  Photo & Video watermarking tool designed for creators, optimized for the global market.
</p>

---

## Overview

AquaMark is a native iOS app (SwiftUI) that provides professional watermarking tools for photos and videos. Designed with international A-tier aesthetics (dark glassmorphism UI), targeting Western markets through the Apple App Store.

### Core Features
- **Photo Watermark** — Text, logo, timestamp, signature overlays with precision controls
- **Video Watermark** — Real-time preview with timeline-based editing
- **Video Crop** — Free crop or preset aspect ratios (1:1, 4:3, 16:9, 9:16)
- **Video Compress** — Smart compression with quality slider
- **MD5 Modifier** — Change file fingerprints without affecting quality
- **Batch Processing** — Process multiple files at once (Pro)

### Monetization
| Plan | Price | Notes |
|------|-------|-------|
| Weekly | $3.99/week | Auto-renewable |
| Monthly | $7.99/month | 3-day free trial |
| Annual | $29.99/year | 7-day free trial, Best Value |
| Lifetime | $49.99 | One-time purchase |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Swift 5.9 |
| UI | SwiftUI (iOS 16+) |
| Architecture | MVVM |
| Media | AVFoundation, CoreImage, PhotosUI |
| Payments | StoreKit 2 |
| Min Target | iOS 16.0 |
| Devices | iPhone + iPad |

---

## Project Structure

```
AquaMark/
├── AquaMark/
│   ├── App/                     # App entry point
│   │   └── AquaMarkApp.swift
│   ├── Core/
│   │   ├── Theme/               # Design system (colors, typography, spacing)
│   │   ├── Components/          # Reusable UI components (GlassCard, ToolCard, etc.)
│   │   └── Extensions/          # Swift extensions
│   ├── Features/
│   │   ├── Home/                # Main tab view + Home screen
│   │   ├── PhotoWatermark/      # Photo watermark editor
│   │   ├── VideoWatermark/      # Video watermark editor
│   │   ├── VideoTools/          # Crop, compress, MD5 tools
│   │   ├── Subscription/        # Paywall + plan selection
│   │   ├── Onboarding/          # First-launch onboarding flow
│   │   └── Settings/            # App settings
│   ├── Services/                # Business logic (SubscriptionManager)
│   ├── Models/                  # Data models
│   ├── Resources/               # Assets, StoreKit config, Info.plist
│   └── Info.plist
├── AppStore/                    # App Store submission materials
│   ├── app_store_listing.md     # Full App Store description + keywords
│   ├── privacy_policy.html      # Privacy policy (ready to host)
│   ├── terms_of_use.html        # Terms of use (ready to host)
│   ├── app_privacy_nutrition_labels.md
│   └── review_preparation.md    # Pre-submission checklist
├── project.yml                  # XcodeGen project spec
└── README.md
```

---

## Setup & Build

### Prerequisites
- macOS 14+ (Sonoma or later)
- Xcode 15+
- Apple Developer Account (Individual or Organization)

### Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd AquaMark

# 2. Generate Xcode project (if using XcodeGen)
brew install xcodegen
xcodegen generate

# 3. Open in Xcode
open AquaMark.xcodeproj

# 4. Configure signing
#    - Select the AquaMark target
#    - Signing & Capabilities tab
#    - Set your Team (Apple Developer account)
#    - Set Bundle Identifier: com.aquamark.app (or your own)

# 5. Run on simulator or device
#    Select iPhone 15 Pro simulator and press Cmd+R
```

### Manual Xcode Project Creation
If not using XcodeGen:
1. Open Xcode → File → New → Project → App
2. Product Name: AquaMark
3. Interface: SwiftUI
4. Language: Swift
5. Drag all files from `AquaMark/` folder into the project
6. Add `AquaMarkProducts.storekit` to the scheme for testing

---

## App Store Submission Guide

### Step 1: Prepare
- [ ] Set your DEVELOPMENT_TEAM in `project.yml` or Xcode
- [ ] Replace `com.aquamark.app` with your own Bundle ID
- [ ] Design and export App Icon (1024x1024px)
- [ ] Take screenshots on required device sizes
- [ ] Host privacy_policy.html and terms_of_use.html on a public URL

### Step 2: App Store Connect
1. Log in to [App Store Connect](https://appstoreconnect.apple.com)
2. Create new app → Fill details from `AppStore/app_store_listing.md`
3. Configure In-App Purchases (4 products from StoreKit config)
4. Fill App Privacy nutrition labels from `app_privacy_nutrition_labels.md`
5. Upload screenshots and app preview

### Step 3: Build & Upload
```bash
# Archive in Xcode
Product → Archive → Distribute App → App Store Connect

# Or use command line
xcodebuild archive -project AquaMark.xcodeproj \
  -scheme AquaMark \
  -archivePath build/AquaMark.xcarchive

xcodebuild -exportArchive \
  -archivePath build/AquaMark.xcarchive \
  -exportPath build/export \
  -exportOptionsPlist ExportOptions.plist
```

### Step 4: Submit for Review
1. Select the uploaded build in App Store Connect
2. Fill Review Notes from `review_preparation.md`
3. Submit for review

---

## What You Need to Do (Owner Actions)

| Task | Why | Time |
|------|-----|------|
| Set DEVELOPMENT_TEAM in Xcode | Code signing requires your Apple Developer cert | 1 min |
| Create App Icon (1024x1024px) | Required for App Store. Recommend: deep purple gradient with water drop | 30 min (or use AI generator) |
| Take screenshots | 3 device sizes required | 20 min |
| Host privacy policy & terms | Must be public URLs | 5 min (use GitHub Pages) |
| Create app in App Store Connect | Requires your Apple ID login | 10 min |
| Configure IAP products | Requires your Apple ID login | 15 min |
| Archive & upload in Xcode | Requires macOS + Xcode | 10 min |
| Submit for review | Final button click | 2 min |

Everything else — code, UI, descriptions, legal docs, review notes — is already done.

---

## Design Philosophy

- **Glassmorphism** — Frosted glass cards with subtle borders
- **Dark-first** — Deep navy/black backgrounds for media editing focus
- **Gradient accents** — Purple-to-pink primary, teal secondary
- **SF Rounded** — Friendly yet professional typography
- **Spring animations** — Natural, physics-based micro-interactions
- **Scale feedback** — Buttons compress on press for tactile feel

Targeting design quality comparable to Darkroom, VSCO, and Canva.

---

## License

Proprietary. All rights reserved.
