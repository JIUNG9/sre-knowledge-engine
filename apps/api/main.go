package main

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"go.uber.org/zap"

	"github.com/junegu/aegis/api/config"
	"github.com/junegu/aegis/api/routes"
)

const banner = `
 _____ _____ _____ _____ _____
|  _  |   __|   __|     |   __|
|     |   __|  |  |-   -|__   |
|__|__|_____|_____|_____|_____|
AI-Native DevSecOps Command Center
`

func main() {
	// Load configuration.
	cfg := config.Load()

	// Initialize structured logger.
	var zapLogger *zap.Logger
	var err error
	if cfg.Environment == "production" {
		zapLogger, err = zap.NewProduction()
	} else {
		zapLogger, err = zap.NewDevelopment()
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer zapLogger.Sync()

	// Print startup banner.
	fmt.Print(banner)
	fmt.Printf("  Version:     0.1.0\n")
	fmt.Printf("  Environment: %s\n", cfg.Environment)
	fmt.Printf("  Port:        %s\n\n", cfg.Port)

	// Create Fiber app.
	app := fiber.New(fiber.Config{
		AppName:               "Aegis API",
		Prefork:               false,
		DisableStartupMessage: true,
	})

	// Apply global middleware.
	app.Use(recover.New())
	app.Use(logger.New(logger.Config{
		Format:     "${time} | ${status} | ${latency} | ${ip} | ${method} ${path}\n",
		TimeFormat: "2006-01-02 15:04:05",
	}))
	app.Use(cors.New(cors.Config{
		AllowOrigins: cfg.CORSOrigins,
		AllowMethods: "GET,POST,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders: "Origin,Content-Type,Accept,Authorization",
	}))

	// Register routes.
	routes.Setup(app, zapLogger)

	// Graceful shutdown.
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-quit
		zapLogger.Info("Shutting down Aegis API server...")
		if err := app.Shutdown(); err != nil {
			zapLogger.Error("Error during shutdown", zap.Error(err))
		}
	}()

	// Start server.
	addr := fmt.Sprintf(":%s", cfg.Port)
	zapLogger.Info("Aegis API server starting", zap.String("addr", addr))
	if err := app.Listen(addr); err != nil {
		zapLogger.Fatal("Failed to start server", zap.Error(err))
	}
}
