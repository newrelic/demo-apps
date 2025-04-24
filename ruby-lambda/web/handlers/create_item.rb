# frozen_string_literal: true
require 'bundler/setup'
require "aws-sdk-dynamodb"

class ItemAlreadyExistsError < StandardError; end

def lambda_handler(event:, context:)
  puts event
  # body = JSON.parse(event["body"])
  item = event["body"].slice("id", "name")

  existing_item = client.get_item(
    table_name: ENV["RUBY_LAMBDA_TABLE"],
    key: { "id" => item["id"] }
  ).item

  raise ItemAlreadyExistsError unless existing_item.nil?

  client.put_item(
    table_name: ENV["RUBY_LAMBDA_TABLE"],
    item: item
  )

  { statusCode: 201, body: item.to_json }
rescue ItemAlreadyExistsError
  { statusCode: 409, body: { error: "Item #{item['id']} already exists" }.to_json }
end

def client
  @client ||= Aws::DynamoDB::Client.new
end
