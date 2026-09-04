.PHONY: test build android windows windows-package up down check

test:
	python -m pytest backend/tests -q

build:
	docker build -f backend/Dockerfile -t mpas-backend:dev backend

android:
	./android/gradlew -p android assembleDebug --no-daemon

windows:
	dotnet publish windows/Mpas.Desktop/Mpas.Desktop.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o windows/dist

windows-package: windows
	cd windows/dist && zip -q -j MPAS-Windows.zip MPAS.Desktop.exe ../README.md

up:
	docker compose up --build --wait

down:
	docker compose down

check: test build
