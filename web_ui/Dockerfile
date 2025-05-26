# Use an official Nginx runtime as a parent image
FROM nginx:stable-alpine

# Set working directory
WORKDIR /usr/share/nginx/html

# Remove default Nginx static assets
# Use * to remove contents instead of the directory itself
RUN rm -rf ./*

# Copy static assets from the web_ui folder to the Nginx html directory
COPY . .

# Expose port 80 to the outside world (standard HTTP port)
EXPOSE 80

# Container startup command (handled by the base image)
# CMD ["nginx", "-g", "daemon off;"]
