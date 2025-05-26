# Use an official Node.js runtime as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install app dependencies
RUN npm install
# Install ca-certificates for HTTPS calls
RUN apk add --no-cache ca-certificates
# If you are building your code for production
# RUN npm ci --omit=dev

# Bundle app source
COPY . .

# Make port ${BACKEND_PORT} available to the world outside this container
# The actual port mapping is done in docker-compose.yml
# We read the port from the environment variable set via docker-compose
# EXPOSE ${BACKEND_PORT}
# Note: EXPOSE doesn't support variable substitution directly in older Docker versions.
# The port mapping in docker-compose handles the exposure.

# Define the command to run the app
CMD [ "node", "server.js" ]
